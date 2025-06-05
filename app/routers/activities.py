from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List # Ensure List is imported (though not used in response_model here directly for POST)
from app.services.activity_service import activity_service, ActivityService
from app.models import Activity, ActivityCreateRequest, DescriptionResponse

async def get_current_activity_service() -> ActivityService:
    return activity_service

router = APIRouter(
    # prefix="/activities", # Defined in main.py
    # tags=["Activities"], # Defined in main.py
    responses={404: {"description": "Not found"}},
)

@router.post("/kr/{kr_iid}", response_model=DescriptionResponse, status_code=200)
async def add_activities_to_key_result_description(
    kr_iid: int = Path(..., title="The IID of the Key Result to add activities to"),
    activity_data: ActivityCreateRequest = Depends(ActivityCreateRequest),
    service: ActivityService = Depends(get_current_activity_service)
):
    try:
        updated_description = service.add_activities_to_kr_description(kr_iid, activity_data.activities)
        return DescriptionResponse(description=updated_description)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add activities to KR {kr_iid}: {str(e)}")

# GET endpoint for activities was previously commented out. Keeping it that way.
