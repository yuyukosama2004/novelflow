from pydantic import BaseModel


class ModelProfileRequest(BaseModel):
    model_profile_id: str | None = None
