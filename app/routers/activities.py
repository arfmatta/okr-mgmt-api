from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List
from app.services.activity_service import activity_service, ActivityService
from app.models import Activity, ActivityCreateRequest # Activity is also used as response model here

# Dependency injector function for ActivityService
async def get_current_activity_service() -> ActivityService:
    return activity_service # Return the globally created instance

router = APIRouter(
    prefix="/activities", # A common prefix for all activity related endpoints
    tags=["Activities"],
    responses={404: {"description": "Not found"}}, # General 404
)

@router.post("/kr/{kr_iid}", response_model=List[Activity], status_code=201)
async def add_activities_to_key_result(
    kr_iid: int = Path(..., title="The IID of the Key Result to add activities to"),
    activity_data: ActivityCreateRequest, # Contains a list of activities
    service: ActivityService = Depends(get_current_activity_service)
):
    """
    Add one or more activities to a specific Key Result (KR).
    The activities are stored within the KR's description.
    Returns the full list of activities for the KR after addition.
    """
    try:
        # The service method expects a list of Activity models
        updated_activities = service.add_activities_to_kr(kr_iid, activity_data.activities)
        return updated_activities
    except ValueError as ve: # e.g., KR not found
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to add activities to KR {kr_iid}: {str(e)}")

@router.get("/kr/{kr_iid}", response_model=List[Activity])
async def get_activities_for_key_result(
    kr_iid: int = Path(..., title="The IID of the Key Result to retrieve activities from"),
    service: ActivityService = Depends(get_current_activity_service)
):
    """
    Get all activities for a specific Key Result (KR).
    Activities are parsed from the KR's description.
    """
    try:
        activities = service.get_activities_for_kr(kr_iid)
        # If KR doesn't exist, service might raise error or return empty list.
        # If service raises an error that should be a 404, it needs to be caught.
        # For now, assume get_activities_for_kr handles KR non-existence gracefully (e.g. by raising its own error or returning empty)
        # If KR issue itself isn't found by gitlab_service.get_issue, it would raise an exception handled by the service or here
        return activities
    except ValueError as ve: # If service explicitly raises ValueError for not found
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        # Log e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve activities for KR {kr_iid}: {str(e)}")

# Note:
# The Pydantic model `Activity` is used directly for response items.
# `ActivityCreateRequest` is used for the POST request body, containing `List[Activity]`.
# This structure means clients send `{"activities": [{activity_1_data}, {activity_2_data}]}`.
# The response for both POST and GET will be `[{activity_1_data}, {activity_2_data}, ...]`
