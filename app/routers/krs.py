from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.services.kr_service import kr_service, KRService # KRService for type hint
from app.models import KRCreateRequest, KRResponse, KRUpdateRequest, User # KRUpdateRequest is new here, Added User
from app.security import get_current_active_user # Added for authentication

async def get_current_kr_service() -> KRService:
    return kr_service

router = APIRouter(
    # prefix="/krs", # Defined in main.py
    # tags=["Key Results (KRs)"], # Defined in main.py
    responses={404: {"description": "KR not found"}},
)

@router.post("/", response_model=KRResponse, status_code=201)
async def create_new_kr(
    kr_data: KRCreateRequest,
    service: KRService = Depends(get_current_kr_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        created_kr = service.create_kr(kr_data)
        return created_kr
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create KR: {str(e)}")

@router.get("/{kr_iid}", response_model=KRResponse)
async def get_specific_kr(
    kr_iid: int,
    service: KRService = Depends(get_current_kr_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        kr = service.get_kr(kr_iid)
        if not kr:
            raise HTTPException(status_code=404, detail="KR not found")
        return kr
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve KR: {str(e)}")

@router.put("/{kr_iid}", response_model=KRResponse)
async def update_existing_kr(
    kr_iid: int,
    kr_data: KRUpdateRequest, # Use the new model for request body
    service: KRService = Depends(get_current_kr_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        updated_kr = service.update_kr(kr_iid=kr_iid, kr_data=kr_data)
        if not updated_kr: # Should not happen if update_kr raises ValueError for not found
            raise HTTPException(status_code=404, detail="KR not found after update attempt")
        return updated_kr
    except ValueError as ve: # Catch ValueError raised by service for not found KR
        raise HTTPException(status_code=404, detail=str(ve)) # Return 404 for not found
    except Exception as e:
        # Log the exception e here for debugging
        raise HTTPException(status_code=500, detail=f"Failed to update KR: {str(e)}")

@router.get("/objective/{objective_iid}", response_model=List[KRResponse])
async def list_krs_for_objective(
    objective_iid: int,
    service: KRService = Depends(get_current_kr_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        krs: List[KRResponse] = service.list_krs_for_objective(objective_iid) # Added type hint
        return krs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list KRs for objective {objective_iid}: {str(e)}")

@router.get("/", response_model=List[KRResponse])
async def list_all_krs_with_label( # Function name implies filtering by label, service.list_all_krs() does this
    service: KRService = Depends(get_current_kr_service),
    current_user: User = Depends(get_current_active_user) # Added dependency
):
    try:
        krs: List[KRResponse] = service.list_all_krs() # Added type hint
        return krs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list all KRs: {str(e)}")
