from pydantic import BaseModel
from typing import List, Optional

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
    # --- Tiered volunteer fields (set only by authenticated NGOs) ---
    ngo_id: Optional[str] = None
    credential_tags: List[str] = []

class NGOInput(BaseModel):
    name: str
    reg_number: str
    lat: float
    lng: float
    radius: float          # operational radius in kilometres
    verified: bool = False