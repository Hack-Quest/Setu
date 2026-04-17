from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


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
    email: str
    password: str
    # --- Tiered volunteer fields (set only by authenticated NGOs) ---
    ngo_id: Optional[str] = None
    credential_tags: List[str] = []


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


class NGOInput(BaseModel):
    name: str
    reg_number: str
    lat: float
    lng: float
    radius: float          # operational radius in kilometres
    verified: bool = False
