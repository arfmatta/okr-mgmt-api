from fastapi import APIRouter, HTTPException, Depends # Removed Body as payload is typed
from app.services.gitlab_service import gitlab_service, GitlabService
from app.models import KRResponse, KRDescriptionUpdateRequest # Added KRDescriptionUpdateRequest
# from gitlab.v4.objects import ProjectIssue # Not directly used in type hints here

# Dependency injector function for GitlabService
async def get_current_gitlab_service() -> GitlabService:
    return gitlab_service

router = APIRouter(
    prefix="/krs",
    tags=["Key Results (KRs) - Description Management"],
    responses={404: {"description": "KR not found"}},
)

# KRDescriptionUpdateRequest is now imported from app.models

@router.put("/{kr_iid}/description", response_model=KRResponse)
async def update_kr_description(
    kr_iid: int,
    payload: KRDescriptionUpdateRequest,
    service: GitlabService = Depends(get_current_gitlab_service)
):
    try:
        updated_issue = service.update_issue( # Renamed variable for clarity
            issue_iid=kr_iid,
            description=payload.description
        )

        return KRResponse(
            id=updated_issue.iid,
            title=updated_issue.title,
            description=updated_issue.description or "",
            web_url=updated_issue.web_url,
            objective_iid=0
        )
    except Exception as e:
        # Add more specific error handling if possible (e.g. for GitlabGetError)
        # from gitlab.exceptions import GitlabGetError
        # if isinstance(e, GitlabGetError):
        #     raise HTTPException(status_code=404, detail=f"KR with IID {kr_iid} not found for update.")
        raise HTTPException(status_code=500, detail=f"Failed to update KR description: {str(e)}")

