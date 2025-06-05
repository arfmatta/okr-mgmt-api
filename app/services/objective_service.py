from app.services import gitlab_service
from app.models import ObjectiveCreateRequest, ObjectiveResponse # Removed GitlabConfig as it's not used
from app.config import settings
from gitlab.v4.objects import ProjectIssue
from typing import List # Ensure List is imported

class ObjectiveService:
    def __init__(self):
        self.gitlab_service = gitlab_service
        self.objective_labels: List[str] = settings.gitlab_objective_labels # Ensure type hint uses List

    def _map_issue_to_objective_response(self, issue: ProjectIssue) -> ObjectiveResponse:
        return ObjectiveResponse(
            id=issue.iid,
            title=issue.title,
            description=issue.description or "",
            web_url=issue.web_url
        )

    def create_objective(self, objective_data: ObjectiveCreateRequest) -> ObjectiveResponse:
        title = f"OBJ{objective_data.obj_number}: {objective_data.title.upper()}"
        description = f"###  Descrição:\n\n> {objective_data.description}\n\n### Resultados Chave"

        labels_to_apply: List[str] = list(set(self.objective_labels)) + [objective_data.team_label, objective_data.product_label]

        try:
            issue = self.gitlab_service.create_issue(
                title=title,
                description=description,
                labels=labels_to_apply
            )
            return self._map_issue_to_objective_response(issue)
        except Exception as e:
            print(f"Error creating objective: {e}")
            raise

    def get_objective(self, objective_iid: int) -> ObjectiveResponse:
        try:
            issue = self.gitlab_service.get_issue(objective_iid)
            return self._map_issue_to_objective_response(issue)
        except Exception as e:
            print(f"Error retrieving objective {objective_iid}: {e}")
            raise

    def list_objectives(self) -> List[ObjectiveResponse]:
        try:
            issues: List[ProjectIssue] = self.gitlab_service.list_issues(labels=self.objective_labels)
            return [self._map_issue_to_objective_response(issue) for issue in issues]
        except Exception as e:
            print(f"Error listing objectives: {e}")
            raise

objective_service = ObjectiveService()
