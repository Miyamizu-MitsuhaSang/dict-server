from typing import List, Tuple

from pydantic import BaseModel

from app.api.user.user_schemas import UserSchema


class CommentPiece(BaseModel):
    user_id: UserSchema
    comment_content: str

    class Config:
        from_attributes = True

class CommentSet(BaseModel):
    comments: List[Tuple[int, str, str]]

    class Config:
        from_attributes = True

class CommentUpload(BaseModel):
    comment_word: str
    comment_content: str
    # lang: Literal["fr", "jp"]