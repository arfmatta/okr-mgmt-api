from fastapi import APIRouter, HTTPException, Depends
from typing import List # Ensure List is imported
from app.services.objective_service import objective_service, ObjectiveService
from app.models import ObjectiveCreateRequest, ObjectiveResponse

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
    service: ObjectiveService = Depends(get_current_objective_service)
):
    try:
        created_objective = service.create_objective(objective_data)
        return created_objective
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create objective: {str(e)}")

@router.get("/", response_model=List[ObjectiveResponse])
async def list_all_objectives(
    service: ObjectiveService = Depends(get_current_objective_service)
):
    try:
        objectives: List[ObjectiveResponse] = service.list_objectives() # Added type hint
        return objectives
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list objectives: {str(e)}")

@router.get("/{objective_iid}", response_model=ObjectiveResponse)
async def get_specific_objective(
    objective_iid: int,
    service: ObjectiveService = Depends(get_current_objective_service)
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
