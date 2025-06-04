from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.services.kr_service import kr_service, KRService # Corrected import
from app.models import KRCreateRequest, KRResponse

# Dependency injector function for KRService
async def get_current_kr_service() -> KRService:
    return kr_service # Return the globally created instance

router = APIRouter(
    prefix="/krs",
    tags=["Key Results (KRs)"],
    responses={404: {"description": "KR not found"}},
)

@router.post("/", response_model=KRResponse, status_code=201)
async def create_new_kr(
    kr_data: KRCreateRequest,
    service: KRService = Depends(get_current_kr_service)
):
    """
    Create a new Key Result (KR).
    The KR will be linked to the specified `objective_iid`.
    """
    try:
        created_kr = service.create_kr(kr_data)
        return created_kr
    except ValueError as ve: # Catch specific errors like Objective not found from service
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to create KR: {str(e)}")

@router.get("/{kr_iid}", response_model=KRResponse)
async def get_specific_kr(
    kr_iid: int,
    service: KRService = Depends(get_current_kr_service)
):
    """
    Get a specific Key Result by its IID.
    """
    try:
        kr = service.get_kr(kr_iid)
        if not kr:
            raise HTTPException(status_code=404, detail="KR not found")
        # Note: The objective_iid in the response might be 0 if not determined by get_kr
        return kr
    except HTTPException:
        raise
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve KR: {str(e)}")

@router.get("/objective/{objective_iid}", response_model=List[KRResponse])
async def list_krs_for_objective(
    objective_iid: int,
    service: KRService = Depends(get_current_kr_service)
):
    """
    List all Key Results (KRs) for a given Objective IID.
    """
    try:
        krs = service.list_krs_for_objective(objective_iid)
        # KRResponse objects from this list should have the correct objective_iid
        return krs
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to list KRs for objective {objective_iid}: {str(e)}")

@router.get("/", response_model=List[KRResponse])
async def list_all_krs_with_label(
    service: KRService = Depends(get_current_kr_service)
):
    """
    List all KRs that have the defined KR label(s).
    Note: The objective_iid in these responses might be 0 if not determinable by list_all_krs.
    """
    try:
        krs = service.list_all_krs()
        return krs
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to list all KRs: {str(e)}")

# Future:
# - Update KR (would likely involve updating fields and possibly re-parsing description if meta changes)
# - Delete KR (GitLab issues are typically closed, not deleted)
# - Endpoints for managing activities within a KR (could be nested or separate)
#   e.g. POST /krs/{kr_iid}/activities
#        GET /krs/{kr_iid}/activities
#   These would use the ActivityService.
