from typing import Tuple

from fastapi import APIRouter, Depends

from app.models import User, CommentFr, CommentJp
from app.schemas.comment_schemas import CommentUpload
from app.utils.security import get_current_user

comment_router = APIRouter()


@comment_router.post("/make-comment")
async def new_word_comment(
        upload: CommentUpload,
        user: Tuple[User, dict] = Depends(get_current_user)
) -> None:
    if upload.lang == "fr":
        await CommentFr.create(
            user=user[0],
            comment_text=upload.comment_content,
            comment_word=upload.comment_word,
        )
    else:
        await CommentJp.create(
            user=user[0],
            comment_text=upload.comment_content,
            comment_word=upload.comment_word,
        )
