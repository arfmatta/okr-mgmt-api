from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

# --- Objective Models ---
class ObjectiveCreateRequest(BaseModel):
    obj_number: int
    title: str
    description: str
    team_label: str
    product_label: str

class ObjectiveResponse(BaseModel):
    id: int # GitLab issue IID
    title: str
    description: str
    web_url: HttpUrl

# --- Key Result (KR) Models ---
class KRCreateRequest(BaseModel):
    objective_iid: int # IID of the parent objective issue
    kr_number: int
    title: str
    description: str # Detailed description of the KR itself
    meta_prevista: int = Field(..., ge=0, le=100) # Percentage
    meta_realizada: int = Field(default=0, ge=0, le=100) # Percentage
    team_label: str
    product_label: str
    responsaveis: List[str]

class KRResponse(BaseModel):
    id: int # GitLab issue IID
    title: str
    description: str # Full description from GitLab, includes metadata and activities table
    web_url: HttpUrl
    objective_iid: int # IID of the linked objective

class KRDetailResponse(BaseModel):
    id: int # GitLab issue IID
    web_url: HttpUrl
    objective_iid: int # IID of the parent objective issue
    kr_number: int
    title: str
    description: str # Detailed description of the KR itself
    meta_prevista: int = Field(..., ge=0, le=100) # Percentage
    meta_realizada: int = Field(default=0, ge=0, le=100) # Percentage
    team_label: str
    product_label: str
    responsaveis: List[str]

class KRDescriptionUpdateRequest(BaseModel):
    description: str

class KRUpdateRequest(BaseModel):
    description: Optional[str] = None
    meta_prevista: Optional[int] = Field(default=None, ge=0, le=100) # Percentage
    meta_realizada: Optional[int] = Field(default=None, ge=0, le=100) # Percentage
    responsaveis: Optional[List[str]] = None

# --- Activity Models ---
class Activity(BaseModel):
    project_action_activity: str
    stakeholders: str
    deadline_planned: str # e.g., "Month/Year" or specific date string
    deadline_achieved: Optional[str] = None
    progress_planned_percent: int = Field(..., ge=0, le=100)
    progress_achieved_percent: int = Field(default=0, ge=0, le=100)

class ActivityCreateRequest(BaseModel):
    activities: List[Activity]

# --- General Utility Models ---
class DescriptionResponse(BaseModel):
    description: str

# --- User Model ---
class User(BaseModel):
    username: str # Or user_id: str, or sub: str, depending on what's in the token
    # Add other fields as needed later, e.g., email, full_name, disabled, roles etc.

# --- GitlabConfig Model (Originally planned here, can also be in config.py if only used there) ---
# For now, keeping it here as it defines a data structure.
# If it were BaseSettings, it would definitely be in config.py.
class GitlabConfig(BaseModel): # Not used by the app currently, but part of original plan
    api_url: HttpUrl
    access_token: str
    project_id: str
    objective_labels: List[str] # Names of labels
    kr_labels: List[str]        # Names of labels
