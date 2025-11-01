import json
import os
import random
import tempfile
from typing import Literal, Tuple, Dict

import azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from starlette.requests import Request

from app.api.pronounciation_test import service
from app.models import PronunciationTestFr, User, PronunciationTestJp
from app.utils.security import get_current_user
from settings import settings

pron_test_router = APIRouter()

AZURE_KEY = settings.AZURE_SUBSCRIPTION_KEY
SERVICE_REGION = "eastasia"

speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=SERVICE_REGION)
audio_config = speechsdk.audio.AudioConfig(filename="test.wav")


@pron_test_router.get("/start")
async def start_test(
        request: Request,
        count: int = 20,
        lang: Literal["fr-FR", "ja-JP"] = Form("fr-FR"),
        user: Tuple[User, Dict] = Depends(get_current_user)
):
    """
       开始新的发音测评会话：
       - 若存在未完成测试，则自动恢复；
       - 若无会话，则随机选取句子并创建新的 session；
       - 支持多语言（法语/日语）。
       """
    redis = request.app.state.redis
    user_id = user[0].id

    key = f"test_session:{user_id}"
    data = await redis.get(key)

    # === 若存在未完成的测试会话 ===
    if data:
        session = json.loads(data)
        return {
            "ok": True,
            "resumed": True,
            "message": "Resumed existing test",
            "session": session
        }

    # === 根据语言选择对应题库 ===
    if lang == "fr-FR":
        total_count = await PronunciationTestFr.all().count()
        table = PronunciationTestFr
    elif lang == "ja-JP":
        total_count = await PronunciationTestJp.all().count()
        table = PronunciationTestJp
    else:
        raise HTTPException(status_code=400, detail="Unsupported language code")

    # === 随机抽取句子 ID ===
    if total_count == 0:
        raise HTTPException(status_code=404, detail=f"No test sentences found for {lang}")

    selected = random.sample(range(1, total_count + 1), k=min(count, total_count))

    # === 构建并保存会话 ===
    session = {
        "lang": lang,  # ← 新增语言字段
        "current_index": 0,
        "sentence_ids": selected,
        "total": len(selected),
    }

    await redis.set(key, json.dumps(session), ex=3600)

    return {
        "ok": True,
        "resumed": False,
        "message": f"New {lang} test started",
        "session": session
    }


@pron_test_router.post("/sentence_test")
async def pron_sentence_test(
        request: Request,
        record: UploadFile = File(...),
        lang: Literal["fr-FR", "ja-JP"] = Form("fr-FR"),
        user: Tuple[User, Dict] = Depends(get_current_user)
):
    """
    目前暂时只提供打分服务，不支持回听录音
    :param request:
    :param record:
    :param lang:
    :param user:
    :return:
    """
    redis = request.app.state.redis
    user_id = user[0].id

    key = f"test_session:{user_id}"
    data = await redis.get(key)
    if not data:
        return {"ok": False, "error": "No active test session"}

    session = json.loads(data)
    sentence_ids = session["sentence_ids"]
    index = session["current_index"]

    if index >= len(sentence_ids):
        await redis.delete(key)
        return {"ok": True, "finished": True, "message": "All sentences tested"}

    sentence_id = sentence_ids[index]
    sentence = await PronunciationTestFr.get(id=sentence_id)
    if not sentence:
        raise HTTPException(status_code=404, detail=f"Sentence {sentence_id} not found")
    text = sentence.text

    if not record.filename.endswith(".wav"):
        raise HTTPException(status_code=415, detail="Invalid file suffix, only '.wav' supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(record.filename)[1]) as tmp:
        tmp.write(await record.read())
        tmp.flush()
        src_path = tmp.name

    # 调用转换函数
    norm_path = src_path + "_norm.wav"
    result = service.convert_to_pcm16_mono_wav(src_path, norm_path)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # 再验证格式
    if not service.verify_audio_format(norm_path):
        raise HTTPException(status_code=415, detail="Invalid audio format")

    try:
        result = service.assess_pronunciation(norm_path, text, lang)
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result)
    except HTTPException as e:
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        os.remove(norm_path)

    await service.save_pron_result(
        redis=redis,
        user_id=user[0].id,
        sentence_id=sentence_id,
        text=text,
        scores=result,
        expire=3600
    )

    session["current_index"] += 1
    await redis.set(key, json.dumps(session), ex=3600)

    result["progress"] = f"{session['current_index']}/{len(sentence_ids)}"

    return {"ok": True, "data": result}


@pron_test_router.get("/current_sentence")
async def get_current_sentence(
        request: Request,
        user: Tuple[User, Dict] = Depends(get_current_user),
):
    redis = request.app.state.redis
    user_id = user[0].id

    key = f"test_session:{user_id}"
    data = await redis.get(key)
    if not data:
        return {"ok": False, "error": "No active test session"}

    session = json.loads(data)
    sentence_ids = session["sentence_ids"]
    index = session["current_index"]
    if index >= len(sentence_ids):
        return {"ok": True, "finished": True, "message": "All sentences tested"}
    sentence_id = sentence_ids[index]
    sentence = await PronunciationTestFr.get(id=sentence_id)
    if not sentence:
        return {"ok": False, "error": "Sentence not found"}
    text = sentence.text

    return {
        "ok": True,
        "index": index,
        "current_sentence": text,
    }


@pron_test_router.post("/testlist")
async def get_testlist(
        request: Request,
        user: Tuple[User, Dict] = Depends(get_current_user),
):
    redis = request.app.state.redis
    user_id = user[0].id

    key = f"test_session:{user_id}"
    data = await redis.get(key)
    if not data:
        return {"ok": False, "error": "No active test session"}

    session = json.loads(data)
    sentence_ids = session["sentence_ids"]
    sentences = []

    for sentence_id in sentence_ids:
        sentence = await PronunciationTestFr.get(id=sentence_id)
        if not sentence:
            raise HTTPException(status_code=404, detail=f"Sentence {sentence_id} not found")
        text = sentence.text
        sentences.append({"id": sentence_id, "text": text})

    return sentences


@pron_test_router.post("/finish")
async def finish_test(
        request: Request,
        confirm: bool = Form(False),
        user: Tuple[User, Dict] = Depends(get_current_user),
):
    """
    结束测试：
    - 若用户未开始测试 → 返回提示；
    - 若测试未完成且 confirm=False → 返回提示；
    - 若测试未完成但 confirm=True → 强制结束，返回已完成部分结果；
    - 若测试已完成 → 返回完整成绩并清除缓存。
    """
    redis = request.app.state.redis
    user_id = user[0].id
    session_key = f"test_session:{user_id}"

    session_data = await redis.get(session_key)
    if not session_data:
        return {"ok": False, "message": "No active test session to finish"}

    session = json.loads(session_data)
    current_index = session.get("current_index", 0)
    sentence_ids = session.get("sentence_ids", [])
    total = len(sentence_ids)
    lang = session["lang"]

    if current_index < len(sentence_ids):
        remaining = total - current_index
        # 如果没有确认，则提醒用户
        if not confirm:
            return {
                "ok": False,
                "unfinished": True,
                "message": f"Test not finished. {remaining} sentence(s) remaining. "
                           "Resend with confirm=true to force end and view partial results."
            }

        # 如果用户确认强制结束，则读取已完成部分成绩
        result = await service.get_pron_result(redis, user_id, delete_after=True)
        await redis.delete(session_key)

        return {
            "ok": True,
            "forced_end": True,
            "message": f"⚠️ Test forcefully ended. {current_index}/{total} sentences completed.",
            "data": result
        }

    # === 已完成测试 ===
    result = await service.get_pron_result(redis, user_id, delete_after=True)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))
    # 删除 Redis session
    await redis.delete(session_key)

    # 存入数据库
    record = await service.record_test_result(user=user[0], result=result, lang=lang)

    return {
        "ok": True,
        "message": "Test session cleared",
        "data": result
    }


@pron_test_router.post("/clear_session")
async def clear_session(request: Request, user: Tuple[User, Dict] = Depends(get_current_user)):
    """
    用户在未完成测试的情况下选择退出，询问是否保存进度，如果不保存则调用本接口清除 Redis
    """
    redis = request.app.state.redis
    user_id = user[0].id

    key = f"test_session:{user_id}"
    await redis.delete(key)
    return {
        "ok": True,
        "message": "Session cleared",
    }
