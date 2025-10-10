from pydantic import BaseModel, Field


class NatsVarzMetrics(BaseModel):
    mem: int = Field(gt=0)
