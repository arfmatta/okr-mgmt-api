from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.services.objective_service import objective_service, ObjectiveService # Corrected import
from app.models import ObjectiveCreateRequest, ObjectiveResponse
# from app.services.gitlab_service import GitlabService # Not directly used here now
# from app.services import get_gitlab_service, get_objective_service # Removed unused placeholder imports

# Dependency injector function for ObjectiveService
async def get_current_objective_service() -> ObjectiveService:
    return objective_service # Return the globally created instance

router = APIRouter(
    prefix="/objectives",
    tags=["Objectives"],
    responses={404: {"description": "Objective not found"}},
)

@router.post("/", response_model=ObjectiveResponse, status_code=201)
async def create_new_objective(
    objective_data: ObjectiveCreateRequest,
    service: ObjectiveService = Depends(get_current_objective_service)
):
    """
    Create a new Objective.
    """
    try:
        # Assuming create_objective returns the ObjectiveResponse compatible model
        created_objective = service.create_objective(objective_data)
        return created_objective
    except Exception as e:
        # In a real app, log the exception e
        raise HTTPException(status_code=500, detail=f"Failed to create objective: {str(e)}")

@router.get("/", response_model=List[ObjectiveResponse])
async def list_all_objectives(
    service: ObjectiveService = Depends(get_current_objective_service)
):
    """
    List all Objectives.
    """
    try:
        objectives = service.list_objectives()
        return objectives
    except Exception as e:
        # In a real app, log the exception e
        raise HTTPException(status_code=500, detail=f"Failed to list objectives: {str(e)}")

@router.get("/{objective_iid}", response_model=ObjectiveResponse)
async def get_specific_objective(
    objective_iid: int,
    service: ObjectiveService = Depends(get_current_objective_service)
):
    """
    Get a specific Objective by its IID (GitLab Issue IID).
    """
    try:
        objective = service.get_objective(objective_iid)
        if not objective: # Assuming service returns None if not found
            raise HTTPException(status_code=404, detail="Objective not found")
        return objective
    except HTTPException: # Re-raise HTTPException directly if service raised it (e.g. 404 from GitLab service)
        raise
    except Exception as e: # Catch other general errors from the service
        # In a real app, log the exception e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve objective: {str(e)}")

# Future: Add PUT / PATCH for updates, DELETE for deletion
# Example:
# @router.put("/{objective_iid}", response_model=ObjectiveResponse)
# async def update_objective(
#     objective_iid: int,
#     objective_update_data: ObjectiveUpdateRequest, # Define this Pydantic model
#     service: ObjectiveService = Depends(get_current_objective_service)
# ):
#     try:
#         updated_objective = service.update_objective(objective_iid, objective_update_data)
#         if not updated_objective:
#             raise HTTPException(status_code=404, detail="Objective not found for update")
#         return updated_objective
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to update objective: {str(e)}")

# Ensure this router is included in the main FastAPI app in app/main.py
# (This was done in a very early subtask for a dummy objectives router)
# Example in app/main.py:
# from app.routers import objectives as objectives_router
# app.include_router(objectives_router.router)
