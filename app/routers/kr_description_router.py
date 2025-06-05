from fastapi import APIRouter, HTTPException, Depends
from app.services.gitlab_service import gitlab_service, GitlabService
from app.models import KRResponse, KRDescriptionUpdateRequest
# No List or Optional needed here directly for type hints beyond what models provide

async def get_current_gitlab_service() -> GitlabService:
    return gitlab_service

router = APIRouter(
    # prefix="/krs", # Defined in main.py
    # tags=["Key Results (KRs) - Description Management"], # Defined in main.py
    responses={404: {"description": "KR not found"}},
)

@router.put("/{kr_iid}/description", response_model=KRResponse)
async def update_kr_description(
    kr_iid: int,
    payload: KRDescriptionUpdateRequest,
    service: GitlabService = Depends(get_current_gitlab_service)
):
    try:
        updated_issue = service.update_issue(
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
        # Consider more specific error handling for GitlabGetError etc.
        raise HTTPException(status_code=500, detail=f"Failed to update KR description: {str(e)}")
