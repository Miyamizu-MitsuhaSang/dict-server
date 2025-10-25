from pydantic import BaseModel, field_validator, ValidationError


class Feedback(BaseModel):
    report_part: str
    text: str

    @classmethod
    @field_validator("report_part")
    def report_part_validator(cls, v):
        types = (
            "ui_design",
            "dict_fr",
            "dict_jp",
            "user",
            "translate",
            "writting",
            "ai_assist",
            "pronounce",
            "comment_api_test",  # 该类型仅作测试使用，不对外暴露
        )
        if v not in types:
            raise ValidationError("Invalid feedback report type")
        return v

    @classmethod
    @field_validator("text")
    def text_validator(cls, v):
        if v is None:
            raise ValidationError("Feedback text cannot be NULL")
        return v

    class Config:
        from_attributes = True
