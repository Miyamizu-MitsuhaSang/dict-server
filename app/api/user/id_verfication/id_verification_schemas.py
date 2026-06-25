from pydantic import BaseModel, field_validator, ValidationError


class IdVerificationRequest(BaseModel):
    real_name: str
    id_number: str

    @field_validator("real_name", "id_number")
    @classmethod
    def request_validator(cls, v):
        if v is None or not v.strip():
            raise ValueError("字段不能为空")
        return v