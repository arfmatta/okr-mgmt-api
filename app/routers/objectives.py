from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional # Ensure List is imported
from app.services.objective_service import objective_service, ObjectiveService
from app.models import ObjectiveCreateRequest, ObjectiveResponse, User, KRDetailResponse # New import for type hint
from app.security import get_current_active_user # New import
# No specific GitlabGetError import needed here if service layer handles not found by returning empty list or generic error

async def get_current_objective_service() -> ObjectiveService:
    return objective_service

router = APIRouter(
    # prefix="/objectives", # Prefix is defined when including router in main.py
    # tags=["Objectives"], # Tags are defined when including router in main.py
    responses={404: {"description": "Objective not found"}},
)

@router.post("/", response_model=ObjectiveResponse, status_code=201)
async def create_new_objective(
    objective_data: ObjectiveCreateRequest,
    service: ObjectiveService = Depends(get_current_objective_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    # The current_user object can be used here if needed, e.g., for logging or ownership
    # For now, its presence means the endpoint is protected.
    try:
        created_objective = service.create_objective(objective_data)
        return created_objective
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create objective: {str(e)}")

@router.get("/", response_model=List[ObjectiveResponse])
async def list_all_objectives(
    service: ObjectiveService = Depends(get_current_objective_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        objectives: List[ObjectiveResponse] = service.list_objectives() # Added type hint
        return objectives
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list objectives: {str(e)}")

@router.get("/{objective_iid}", response_model=ObjectiveResponse)
async def get_specific_objective(
    objective_iid: int,
    service: ObjectiveService = Depends(get_current_objective_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        objective = service.get_objective(objective_iid)
        if not objective:
            raise HTTPException(status_code=404, detail="Objective not found")
        return objective
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve objective: {str(e)}")

@router.get("/{objective_iid}/krs", response_model=List[KRDetailResponse])
async def get_krs_for_objective_endpoint(
    objective_iid: int,
    service: ObjectiveService = Depends(get_current_objective_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves all Key Results (KRs) associated with a specific objective.
    The underlying service method `get_krs_for_objective` fetches the objective first.
    If the objective is not found, the service currently catches the exception and returns an empty list [].
    Therefore, this endpoint will return an empty list if the objective doesn't exist or has no KRs.
    A specific 404 for the objective not being found would require changes in the service layer.
    """
    try:
        krs = service.get_krs_for_objective(objective_iid=objective_iid)
        # If objective_iid itself is invalid causing an error before service call (e.g. path param validation),
        # FastAPI would handle it. If service.get_krs_for_objective has an issue beyond objective not found
        # (which it handles by returning []), it would be caught by the generic exception below.
        return krs
    except Exception as e:
        # This would catch unexpected errors within the service method, other than GitLab's "not found"
        # which the service handles by returning [].
        raise HTTPException(status_code=500, detail=f"Failed to retrieve KRs for objective {objective_iid}: {str(e)}")

@router.get("/by_filters/", response_model=List[ObjectiveResponse]) # Added trailing slash for consistency
async def list_objectives_by_filters_endpoint(
    year: Optional[str] = None,
    team: Optional[str] = None,
    product: Optional[str] = None,
    service: ObjectiveService = Depends(get_current_objective_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        objectives = service.list_objectives_by_filters(year=year, team=team, product=product)
        return objectives
    except ValueError as ve: # Catch specific error from service for invalid filter combination
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Catch any other unexpected errors from the service layer
        raise HTTPException(status_code=500, detail=f"Failed to list objectives by filters: {str(e)}")
