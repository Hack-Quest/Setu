from pydantic import BaseModel, Field, AliasChoices
from typing import List


class NeedInput(BaseModel):
    reporter_name: str
    reporter_phone: str
    location_text: str = Field(
        validation_alias=AliasChoices("location_text", "location")
    )
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


class VolunteerRegisterInput(BaseModel):
    email: str
    password: str
    name: str
    phone: str
    location: str
    skills: List[str]


class VolunteerLoginInput(BaseModel):
    email: str
    password: str
