from fastapi import APIRouter, HTTPException, Depends, Body
from app.services.gitlab_service import gitlab_service, GitlabService
from app.models import KRResponse # To represent the updated KR potentially
from gitlab.v4.objects import ProjectIssue

# Dependency injector function for GitlabService
async def get_current_gitlab_service() -> GitlabService:
    return gitlab_service # Return the globally created instance

router = APIRouter(
    prefix="/krs", # Could also be a more specific prefix like /kr-descriptions
    tags=["Key Results (KRs) - Description Management"],
    responses={404: {"description": "KR not found"}},
)

from pydantic import BaseModel # Import BaseModel

class KRDescriptionUpdateRequest(BaseModel):
    description: str

@router.put("/{kr_iid}/description", response_model=KRResponse) # Or a simpler success message
async def update_kr_description(
    kr_iid: int,
    payload: KRDescriptionUpdateRequest, # Using the new Pydantic model
    service: GitlabService = Depends(get_current_gitlab_service)
):
    """
    Update the full description of a specific Key Result (KR) issue.
    This will overwrite the existing description.
    """
    try:
        # Use gitlab_service to update the issue's description
        updated_issue: ProjectIssue = service.update_issue(
            issue_iid=kr_iid,
            description=payload.description
        )

        # Map the updated GitLab issue to a KRResponse.
        # This mapping might be simplistic if KRResponse expects more than what an issue offers directly
        # or if specific parsing from the new description is needed to populate KRResponse fully.
        # For now, use basic attributes.
        # The KRService._map_issue_to_kr_response could be useful if accessible and appropriate.
        # Let's assume a simple mapping for now, as KRService is not directly used here.
        return KRResponse(
            id=updated_issue.iid,
            title=updated_issue.title,
            description=updated_issue.description or "",
            web_url=updated_issue.web_url,
            objective_iid=0 # This endpoint doesn't know the objective_iid directly
        )
    except Exception as e: # Broadly catching exceptions from the service layer
        # Log e
        # Specific error handling for GitlabGetError (404) vs GitlabUpdateError (could be 400 or 500)
        # from the service would be better. The service currently re-raises them.
        # For now, a general 500, unless we can inspect 'e' more closely.
        # If e is GitlabGetError (from issue not found in update_issue), it should be 404.
        # This requires importing gitlab.exceptions.
        # For simplicity, let's assume the service might raise specific exceptions we can catch,
        # or we default to 500. If GitlabService's get_issue (called by update_issue)
        # raises GitlabGetError and it's not caught and transformed there, it propagates.
        # The current GitlabService does re-raise GitlabGetError.

        # A more refined error handling would be:
        # from gitlab.exceptions import GitlabGetError, GitlabUpdateError
        # if isinstance(e, GitlabGetError):
        #     raise HTTPException(status_code=404, detail=f"KR with IID {kr_iid} not found.")
        # elif isinstance(e, GitlabUpdateError):
        #     raise HTTPException(status_code=400, detail=f"Failed to update KR {kr_iid}: {str(e)}")

        raise HTTPException(status_code=500, detail=f"Failed to update KR description: {str(e)}")

# Note: This router provides a generic way to update the KR's description.
# The calling client is responsible for formatting the description string,
# for example, including Markdown tables for activities if desired.
# This is different from the ActivityService which specifically formats activities.
# This endpoint gives more direct control over the entire description content.
