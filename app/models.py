from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

# --- Objective Models ---
class ObjectiveCreateRequest(BaseModel):
    obj_number: int
    title: str
    description: str

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
    meta_prevista: float = Field(..., ge=0, le=100) # Percentage
    meta_realizada: float = Field(default=0.0, ge=0, le=100) # Percentage
    responsaveis: List[str]

class KRResponse(BaseModel):
    id: int # GitLab issue IID
    title: str
    description: str # Full description from GitLab, includes metadata and activities table
    web_url: HttpUrl
    objective_iid: int # IID of the linked objective

class KRDescriptionUpdateRequest(BaseModel):
    description: str

# --- Activity Models ---
class Activity(BaseModel):
    project_action_activity: str
    stakeholders: str
    deadline_planned: str # e.g., "Month/Year" or specific date string
    deadline_achieved: Optional[str] = None
    progress_planned_percent: float = Field(..., ge=0, le=100)
    progress_achieved_percent: float = Field(default=0.0, ge=0, le=100)

class ActivityCreateRequest(BaseModel):
    activities: List[Activity]

# --- General Utility Models ---
class DescriptionResponse(BaseModel):
    description: str

# --- GitlabConfig Model (Originally planned here, can also be in config.py if only used there) ---
# For now, keeping it here as it defines a data structure.
# If it were BaseSettings, it would definitely be in config.py.
class GitlabConfig(BaseModel): # Not used by the app currently, but part of original plan
    api_url: HttpUrl
    access_token: str
    project_id: str
    objective_labels: List[str] # Names of labels
    kr_labels: List[str]        # Names of labels
