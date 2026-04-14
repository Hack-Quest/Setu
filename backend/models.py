from pydantic import BaseModel
from typing import List

class NeedInput(BaseModel):
    reporter_name: str
    reporter_phone: str
    location: str
    disaster_type: str
    help_needed: str
    description: str

class VolunteerInput(BaseModel):
    name: str
    phone: str
    location: str
    skills: List[str]
    lat: float = 0.0
    lng: float = 0.0