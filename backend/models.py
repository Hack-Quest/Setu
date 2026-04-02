from pydantic import BaseModel

class NeedInput(BaseModel):
    reporter_name: str
    reporter_phone: str
    location: str
    disaster_type: str
    help_needed: str
    description: str