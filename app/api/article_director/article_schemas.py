from pydantic import BaseModel


class UserArticleRequest(BaseModel):
    # theme: Optional[str]
    title_content: str
    article_type: str

class UserQuery(BaseModel):
    query: str