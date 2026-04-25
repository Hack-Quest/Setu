from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional


class NeedInput(BaseModel):
    reporter_name: str = Field(default="Unknown", validation_alias=AliasChoices("reporter_name", "name"))
    reporter_phone: str = Field(default="0000000000", validation_alias=AliasChoices("reporter_phone", "phone"))
    location_text: str = Field(
        default="", validation_alias=AliasChoices("location_text", "location", "address")
    )
    lat: float = 0.0
    lng: float = 0.0
    disaster_type: str = Field(default="Not Specified")
    help_needed: str = Field(default="Not Specified")
    description: str = Field(default="")


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
    ngo_name: str = Field(default="Unknown NGO", validation_alias=AliasChoices("ngo_name", "organization_name", "name", "organization"))
    owner_name: str = Field(default="Unknown Admin", validation_alias=AliasChoices("owner_name", "contact_name", "admin", "owner"))
    reg_number: str = Field(default="PENDING", validation_alias=AliasChoices("reg_number", "registration_number", "reg_no"))
    location: str = Field(default="", validation_alias=AliasChoices("location", "coverage_area"))
    lat: float = 0.0
    lng: float = 0.0
    radius: float = 50.0   # operational radius in kilometres
    verified: bool = False
    coverage_area: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None


class SendOTPInput(BaseModel):
    email: str


class VerifyOTPInput(BaseModel):
    email: str
    otp: str
