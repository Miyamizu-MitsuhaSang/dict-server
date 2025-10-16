from typing import Optional, List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AIQuestionRequest(BaseModel):
    word: str
    question: str


class AIAnswerResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None

    def get_answer(self) -> str:
        """返回第一个回答的文本内容"""
        if self.choices and self.choices[0].message:
            return self.choices[0].message.content
        return ""


class AIAnswerOut(BaseModel):
    word: str
    answer: str
    model: str
    tokens_used: Optional[int] = None
