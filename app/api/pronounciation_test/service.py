import contextlib
import json
import os
import wave
from io import BytesIO
from typing import Literal, Dict, Any, List

import azure.cognitiveservices.speech as speechsdk
from fastapi import HTTPException
from pydub import AudioSegment
from redis.asyncio import Redis

from app.models import User
from app.models.base import UserTestRecord
from settings import settings


# from imageio_ffmpeg import get_ffmpeg_exe
# AudioSegment.converter = get_ffmpeg_exe()


def verify_audio_format(path: str) -> bool:
    """
    检测音频文件是否符合 Azure Speech 要求:
    采样率 16000Hz, 16-bit, 单声道 (PCM).
    返回字典包含格式信息和布尔结果。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found: {path}")

    try:
        with contextlib.closing(wave.open(path, 'rb')) as wf:
            rate = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()

            ok = (rate == 16000 and channels == 1 and width == 2)
            if not ok:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "rate": rate,
                        "channels": channels,
                        "width": width,
                        "message": (
                            f"⚠️ Invalid format (rate={rate}, channels={channels}, width={width}). "
                            "Expected: 16000Hz, mono, 16-bit PCM."
                        )
                    }
                )
    except wave.Error as e:
        raise HTTPException(status_code=401, detail=f"Invalid WAV file: {e}")
    return True

def assess_pronunciation(
        audio_path: str,
        reference_text: str,
        lang: Literal["fr-FR", "ja-JP"] = "fr-FR",
        grading_system: Literal["HundredMark", "FivePoint"] = "FivePoint",
        granularity: Literal["Phoneme", "Word", "FullText"] = "Phoneme",
        enable_miscue: bool = True,
) -> Dict[str, Any]:
    """
    使用 Azure Speech SDK 对音频文件进行发音测评。（增强错误输出版）
    :param audio_path: 音频文件路径（必须是 PCM16/Mono/WAV）
    :param reference_text: 期望朗读的文本
    :param lang: 语种代码，例如 'fr-FR'（法语）、'ja-JP'（日语）、'en-US'（英语）
    :param grading_system: 评分体系 ('HundredMark' / 'FivePoint')
    :param granularity: 评分粒度 ('Phoneme' / 'Word' / 'FullText')
    :param enable_miscue: 是否检测漏读/多读（True 推荐）
    :return: 包含整体分、准确度、流畅度、完整度及识别文本的字典
    """
    # === 1. 加载 Azure Speech 配置 ===
    subsciption_key = settings.AZURE_SUBSCRIPTION_KEY
    region = "eastasia"
    print(">>> Azure Key Loaded:", settings.AZURE_SUBSCRIPTION_KEY[:8], "...")
    print(">>> Azure Region:", "eastasia")

    if not subsciption_key or not region:
        raise RuntimeError("缺少 Azure Speech 环境变量 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION")

    speech_config = speechsdk.SpeechConfig(subscription=subsciption_key, region=region)
    speech_config.speech_recognition_language = lang

    # === 2. 加载音频文件 ===
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print(reference_text)

    # === 3. 构建发音测评配置 ===
    pron_assestment = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=getattr(speechsdk.PronunciationAssessmentGradingSystem, grading_system),
        granularity=getattr(speechsdk.PronunciationAssessmentGranularity, granularity),
        enable_miscue=enable_miscue
    )
    pron_assestment.apply_to(recognizer)

    # === 4. 执行识别与打分 ===
    result = recognizer.recognize_once()

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return __parse_azure_error(result)

    pa_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
    data = json.loads(pa_result)
    pa_data = data["NBest"][0]["PronunciationAssessment"]

    return {
        "ok": True,
        "recognized_text": data.get("DisplayText"),
        "overall_score": pa_data.get("PronScore"),
        "accuracy": pa_data.get("AccuracyScore"),
        "fluency": pa_data.get("FluencyScore"),
        "completeness": pa_data.get("CompletenessScore")
    }

def __parse_azure_error(result: Any) -> Dict[str, Any]:
    """
    从 Azure Speech 识别结果中提取详细错误信息。
    用于处理 ResultReason != RecognizedSpeech 的情况。
    :param result: SpeechRecognizer 的识别结果对象
    :return: 包含 ok=False 与详细错误字段的 dict
    """
    err_data = {
        "ok": False,
        "error": str(result.reason),
        "details": getattr(result, "error_details", None)
    }

    # ① 无法识别语音（NoMatch）
    if result.reason == speechsdk.ResultReason.NoMatch:
        err_data["no_match_details"] = str(getattr(result, "no_match_details", None))
        print("[Azure] ⚠️ NoMatch: Speech could not be recognized.")
        print(f"[Azure] Details: {err_data['no_match_details']}")

    # ② 请求被取消（Canceled）
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = getattr(result, "cancellation_details", None)
        if cancellation_details:
            err_data["cancel_reason"] = str(getattr(cancellation_details, "reason", None))
            err_data["cancel_error_details"] = getattr(cancellation_details, "error_details", None)
            err_data["cancel_error_code"] = getattr(cancellation_details, "error_code", None)

            print("[Azure] ❌ Canceled by Speech Service")
            print(f"[Azure] Reason: {err_data['cancel_reason']}")
            print(f"[Azure] Error details: {err_data['cancel_error_details']}")
            print(f"[Azure] Error code: {err_data['cancel_error_code']}")
        else:
            print("[Azure] ❌ Canceled but no details provided.")

    # ③ 其他未知类型
    else:
        print(f"[Azure] ⚠️ Unexpected recognition result: {result.reason}")
        print(f"[Azure] Error details: {err_data['details']}")

    return err_data

def convert_to_pcm16_mono_wav(input_path: str, output_path: str):
    """
        将任意音频格式转换为 Azure Speech API 要求的标准 WAV 文件:
        - 采样率 16 kHz
        - 单声道
        - 16 bit PCM
        """
    from pydub import AudioSegment

    try:
        audio = AudioSegment.from_file(input_path)
        duration_ms = len(audio)

        # 重新采样
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(output_path, format="wav")

        return {
            "ok": True,
            "path": output_path,
            "message": f"Converted successfully ({duration_ms / 1000:.2f}s)"
        }

    except Exception as e:
        return {
            "ok": False,
            "path": None,
            "message": f"Audio conversion failed: {str(e)}"
        }

def convert_audio_to_memory(file_obj):
    """
    完全在内存中转化（更快）
    :param file_obj:
    :return: 转换后的 BinaryStream
    """
    audio = AudioSegment.from_file(file_obj)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    buf = BytesIO()
    audio.export(buf, format="wav")
    buf.seek(0)
    return buf

async def save_pron_result(
    redis: Redis,
    user_id: int,
    sentence_id: int,
    text: str,
    scores: Dict[str, float],
    expire: int = 3600
) -> None:
    """
    将测评结果保存到 Redis。
    结构：test_result:{user_id} -> {"sentences": [ {...}, {...} ]}
    """
    key = f"test_result:{user_id}"
    existing = await redis.get(key)
    if existing:
        data = json.loads(existing)
    else:
        data = {"sentences": []}

    # 防止重复写入同一条 sentence_id
    if not any(item["id"] == sentence_id for item in data["sentences"]):
        entry = {
            "id": sentence_id,
            "text": text,
            "overall": scores.get("overall_score"),
            "accuracy": scores.get("accuracy"),
            "fluency": scores.get("fluency"),
            "completeness": scores.get("completeness")
        }
        data["sentences"].append(entry)
        await redis.set(key, json.dumps(data), ex=expire)

async def get_pron_result(
    redis: Redis,
    user_id: int,
    delete_after: bool = False
) -> Dict[str, Any]:
    """
    从 Redis 获取用户的所有句子测评结果，
    返回每句分数 + 总分 + 平均分 + 等级评定。
    """
    key = f"test_result:{user_id}"
    data = await redis.get(key)

    if not data:
        return {"ok": False, "error": "No result found"}

    result_data = json.loads(data)
    sentences: List[Dict[str, Any]] = result_data.get("sentences", [])

    if not sentences:
        return {"ok": False, "error": "Empty result list"}

    fields = ["overall", "accuracy", "fluency", "completeness"]

    # 计算总分与平均分
    totals = {f: 0.0 for f in fields}
    counts = {f: 0 for f in fields}
    for s in sentences:
        for f in fields:
            if s.get(f) is not None:
                totals[f] += s[f]
                counts[f] += 1

    averages = {
        f: round(totals[f] / counts[f], 2) if counts[f] else 0.0
        for f in fields
    }

    # 等级映射函数
    def grade(score: float) -> str:
        if score >= 4.5:
            return "优秀 🏆"
        elif score >= 3.5:
            return "良好 👍"
        elif score >= 2.5:
            return "一般 🙂"
        elif score > 0:
            return "需改进 ⚠️"
        return "无数据"

    # 各项等级 + 总体等级
    grade_map = {f: grade(averages[f]) for f in fields}
    grade_map["overall_level"] = grade(averages["overall"])

    if delete_after:
        await redis.delete(key)

    return {
        "ok": True,
        "count": len(sentences),
        "totals": {f: round(totals[f], 2) for f in fields},
        "average": averages,
        "grades": grade_map,
        "sentences": sentences
    }

async def record_test_result(
    user: User,
    result: Dict[str, Any],
    lang: Literal["fr", "jp"]
) -> Dict[str, Any]:
    """
    将一次完整测评结果写入数据库。

    :param user: 当前用户对象
    :param result: 从 get_pron_result() 返回的结果字典
    :param lang: 测试语种 ('fr' 或 'jp')
    :return: 数据库存储结果摘要
    """
    if not result.get("ok"):
        return {"ok": False, "error": "Invalid test result"}

    avg = result.get("average", {})
    grades = result.get("grades", {})
    count = result.get("count", 0)
    sentences = result.get("sentences", [])

    # 构建可存储的数据
    record = await UserTestRecord.create(
        user=user,  # 外键绑定用户对象
        username=user.name,
        language=lang,
        total_sentences=count,
        average_score=avg.get("overall", 0.0),
        accuracy_score=avg.get("accuracy", 0.0),
        fluency_score=avg.get("fluency", 0.0),
        completeness_score=avg.get("completeness", 0.0),
        level=grades.get("overall_level", "无"),
        raw_result=json.dumps(result, ensure_ascii=False),
    )

    return {
        "ok": True,
        "id": record.id,
        "user": user.name,
        "language": lang,
        "average_score": avg.get("overall"),
        "level": grades.get("overall_level"),
        "count": count,
        "timestamp": record.created_at.isoformat()
    }