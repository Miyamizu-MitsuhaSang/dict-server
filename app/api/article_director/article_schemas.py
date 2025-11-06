from typing import Optional

from pydantic import BaseModel


class UserArticleRequest(BaseModel):
    theme: Optional[str]
    content: str
    article_type: str

class UserQuery(BaseModel):
    query: str