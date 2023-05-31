from pydantic import BaseModel


class Limit(BaseModel):
    key: str
    value: int
    ttl: int
