from tortoise.signals import pre_save
from tortoise import BaseDBAsyncClient
from typing import Optional

from app.utils.textnorm import normalize_text
from app.models.fr import WordlistFr


@pre_save(WordlistFr)
async def wordlist_fr_pre_save(
        sender: type[WordlistFr],
        instance: WordlistFr,
        using_db: BaseDBAsyncClient,
        update_fields: Optional[list[str]]
) -> None:
    """
        仅当 text 变更时，同步 search_text。
        - 新建：总是写入 search_text
        - 修改：只有当 text 在本次更新范围内，或 text 实际发生变化时才更新
        - 若调用方用了 update_fields，只包含 text，则自动把 'search_text' 追加进去，确保写回
    """
    desired = normalize_text(instance.text or "")
    # 不变则不写，减少无谓 UPDATE
    if instance.search_text == desired:
        return

    # 情况 1：完整更新（没有传 update_fields）
    if update_fields is None:
        instance.search_text = desired
        return  # ✅ 会写入

    # 情况 2：部分更新——只有当这次确实更新了 text，才同步 search_text
    if "text" in update_fields:
        instance.search_text = desired
        # update_fields 可能是 tuple，转成 list 再补充
        fields = list(update_fields)
        if "search_text" not in fields:
            fields.append("search_text")
        # 交还给 ORM：确保此次 UPDATE 包含 search_text
        instance._update_fields = fields
    # 否则（这次没更 text），不动 search_text
