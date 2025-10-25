from typing import Literal, Tuple

from fastapi import APIRouter, Depends

from app.api.word_comment.word_comment_schemas import CommentUpload
from app.models import User, CommentFr, CommentJp
from app.utils.security import get_current_user

word_comment_router = APIRouter()

@word_comment_router.post("/{lang}")
async def create_word_comment(
        lang: Literal["jp", "fr"],
        upload: CommentUpload,
        user: Tuple[User, dict] = Depends(get_current_user)
):
    if lang == "fr":
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