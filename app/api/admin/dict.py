from fastapi import Depends, HTTPException, Request, Query
from typing import Literal, Tuple, Union

from tortoise.exceptions import DoesNotExist

from app.models.base import User
from app.models.fr import DefinitionFr
from app.utils.security import get_current_user
from app.api.admin.router import admin_router
import app.models.fr as fr
import app.models.jp as jp
from app.schemas.admin_schemas import CreateWord, UpdateWordSet, UpdateWord, SearchWordRequest


@admin_router.get("/dict")
async def get_wordlist(request: Request,
                       page: int = Query(1, ge=1),
                       page_size: int = Query(10, le=10),
                       lang_code: Literal["fr", "jp"] = "fr",
                       admin_user: Tuple[User, dict] = Depends(get_current_user)):
    """
    后台管理系统中关于词典部分的初始界面，分页显示
    :param request: 请求头
    :param page: 显示的表格视窗的页数，起始默认为 1
    :param page_size: 控制每页的单词内容条数
    :param lang_code: 查询并显示对应语言的单词表
    :return: None
    """
    if not admin_user[0].is_admin:
        raise HTTPException(status_code=403, detail="非管理员，无权限访问")
    offset = (page - 1) * page_size
    if lang_code == "fr":
        total = await fr.DefinitionFr.all().count()
        wordlist = await fr.DefinitionFr.all().offset(offset).limit(page_size).values(
            "word__text",
            "pos",
            "meaning",
            "example",
            "eng_explanation"
        )
    else:
        total = await jp.DefinitionJp.all().count()
        wordlist = await jp.DefinitionJp.all().offset(offset).limit(page_size).values(
            "word__text",
            "pos",
            "meaning",
            "example",
        )
    return {
        "total": total,
        "data": wordlist
    }


@admin_router.post("/dict/search_word")
async def search_word(
        request: Request,
        search_word: SearchWordRequest,
        admin_user: Tuple[User, dict] = Depends(get_current_user),
):
    """
    查询单词
    :param request: 请求体参数
    :param search_word: Pydantic 模型校验：可提供词性筛选
    :param admin_user:
    :return:
    """
    if not admin_user[0].is_admin:
        raise HTTPException(status_code=403, detail="非管理员，无权限访问")
    # 筛选参数构造
    filter_kwargs = {}
    if search_word.pos:
        filter_kwargs["pos"] = search_word.pos
    if search_word.language == "fr":
        try:
            word_obj = await fr.WordlistFr.get(text=search_word.word)
        except DoesNotExist:
            raise HTTPException(status_code=400, detail=f"词条 {search_word.word} 不存在于法语词表中")
        definitions = await word_obj.definitions.filter(**filter_kwargs)
        result = [{
            "id": d.id,
            "word": word_obj.text,
            "pos": d.pos,
            "meaning": d.meaning,
            "example": d.example,
            "eng_explanation": d.eng_explanation
        } for d in definitions]
        return result
    else:
        try:
            word_obj = await jp.WordlistJp.get(text=search_word.word)
        except DoesNotExist:
            raise HTTPException(status_code=400, detail=f"词条 {search_word.word} 不存在于日语词表中")
        definitions = await word_obj.definitions.filter(**filter_kwargs)
        result = [{
            "id": d.id,
            "word": word_obj.text,
            "pos": d.pos,
            "meaning": d.meaning,
            "example": d.example
        } for d in definitions]
        return result


@admin_router.post("/dict/adjust")
async def adjust_dict(
        request: Request,
        updated_contents: UpdateWordSet,
        admin_user: Tuple[User, dict] = Depends(get_current_user)
):
    """
    只关心更新的内容，不关心未改变的内容。
    批量更新 Definition 项，跳过失败项但记录错误。
    :param request:
    :param updated_contents:
    :param admin_user:
    :return:
    """

    if not admin_user[0].is_admin:
        raise HTTPException(status_code=403, detail="非管理员，无权限访问")

    if updated_contents.count() == 0:
        raise HTTPException(status_code=422, detail="无改动信息")

    errors = []

    async def update_definition(update_word: UpdateWord) -> None:
        # 检查词条是否存在
        if update_word.language == 'fr':
            word_entry = await fr.WordlistFr.get_or_none(id=update_word.id)
            if not word_entry:
                raise HTTPException(status_code=400, detail=f"词条 ID {update_word.id} 不存在于法语词表中")
            update_obj = await fr.DefinitionFr.get_or_none(id=update_word.id)
        else:
            word_entry = await jp.WordlistJp.get_or_none(id=update_word.id)
            if not word_entry:
                raise HTTPException(status_code=400, detail=f"词条 ID {update_word.id} 不存在于日语词表中")
            update_obj = await jp.DefinitionJp.get_or_none(id=update_word.id)

        if not update_obj:
            raise HTTPException(status_code=404, detail=f"定义 ID {update_word.id} 不存在")

        # 获取更新字段
        update_data = update_word.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field != "id":
                setattr(update_obj, field, value)

        await update_obj.save()

    for updated_content in updated_contents:
        try:
            await update_definition(updated_content)
        except HTTPException as e:
            errors.append({
                "id": updated_content.id,
                "error": e.detail
            })

    return {
        "msg": "更新完成",
        "success_count": updated_contents.count() - len(errors),
        "fail_count": len(errors),
        "errors": errors
    }


@admin_router.post("/dict/add")
async def add_dict(
        request: Request,
        new_word: CreateWord,
        admin_user: Tuple[User, dict] = Depends(get_current_user)
) -> None:
    if not admin_user[0].is_admin:
        raise HTTPException(status_code=403, detail="非管理员，无权限访问")
    if new_word.language == "fr":
        cls_word, _ = await fr.WordlistFr.get_or_create(text=new_word.word)
        new_definition, created = await fr.DefinitionFr.get_or_create(
            word=cls_word,
            pos=new_word.pos,
            meaning=new_word.meaning,
            example=new_word.example,
            eng_explanation=new_word.eng_explanation
        )
        if not created:
            raise HTTPException(status_code=409, detail="释义已存在")
    elif new_word.language == "jp":
        cls_word, _ = await jp.WordlistJp.get_or_create(text=new_word.word)
        new_definition, created = await jp.DefinitionJp.get_or_create(
            word=cls_word,
            pos=new_word.pos,
            meaning=new_word.meaning,
            example=new_word.example,
        )
        if not created:
            raise HTTPException(status_code=409, detail="释义已存在")
    else:
        raise HTTPException(status_code=400, detail="暂不支持语言类型")
