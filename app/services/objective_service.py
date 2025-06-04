from app.services import gitlab_service # Using the instance
from app.models import ObjectiveCreateRequest, ObjectiveResponse, GitlabConfig # Assuming models are in app.models
from app.config import settings
from gitlab.v4.objects import ProjectIssue
from typing import List

class ObjectiveService:
    def __init__(self):
        self.gitlab_service = gitlab_service # Use the shared instance
        self.objective_labels = settings.gitlab_objective_labels

    def _map_issue_to_objective_response(self, issue: ProjectIssue) -> ObjectiveResponse:
        """Helper to map a GitLab issue to an ObjectiveResponse model."""
        return ObjectiveResponse(
            id=issue.iid,
            title=issue.title,
            description=issue.description or "", # Ensure description is not None
            web_url=issue.web_url
        )

    def create_objective(self, objective_data: ObjectiveCreateRequest) -> ObjectiveResponse:
        """
        Creates an objective as a GitLab issue.
        """
        title = f"OBJ{objective_data.obj_number}: {objective_data.title.upper()}" # Title in uppercase
        description = f"###  Descrição:\n\n> {objective_data.description}\n\n### Resultados Chave" # Markdown formatted description

        # Combine with default objective labels from settings
        labels_to_apply = list(set(self.objective_labels)) # Avoid duplicates if any

        try:
            issue = self.gitlab_service.create_issue(
                title=title,
                description=description,
                labels=labels_to_apply
            )
            return self._map_issue_to_objective_response(issue)
        except Exception as e:
            # Log the error e
            print(f"Error creating objective: {e}") # Replace with actual logging
            raise # Re-raise or handle appropriately

    def get_objective(self, objective_iid: int) -> ObjectiveResponse:
        """
        Retrieves a specific objective (GitLab issue) by its IID.
        """
        try:
            issue = self.gitlab_service.get_issue(issue_iid)
            # Basic check if it's an objective - ideally, it should have the objective labels
            # For simplicity, we assume any issue retrieved by IID here is intended to be an objective
            # A more robust check would verify labels if necessary.
            return self._map_issue_to_objective_response(issue)
        except Exception as e:
            # Log the error e
            print(f"Error retrieving objective {objective_iid}: {e}") # Replace with actual logging
            raise

    def list_objectives(self) -> List[ObjectiveResponse]:
        """
        Lists all objectives (GitLab issues with specific labels).
        """
        try:
            # Use the objective labels from settings to filter issues
            issues = self.gitlab_service.list_issues(labels=self.objective_labels)
            return [self._map_issue_to_objective_response(issue) for issue in issues]
        except Exception as e:
            # Log the error e
            print(f"Error listing objectives: {e}") # Replace with actual logging
            raise

# Instantiate the service for potential direct use or for routers to import
objective_service = ObjectiveService()

# Example Usage (for testing - would require .env and live GitLab)
# if __name__ == "__main__":
#     print("Testing ObjectiveService...")
#     # Ensure GITLAB_ACCESS_TOKEN, GITLAB_PROJECT_ID, GITLAB_OBJECTIVE_LABELS are in .env
#     # e.g., GITLAB_OBJECTIVE_LABELS="Objective,StrategicGoal"
#
#     if not settings.gitlab_access_token or not settings.gitlab_project_id:
#         print("GitLab credentials or project ID not set in .env. Exiting test.")
#     else:
#         print(f"Objective labels being used: {settings.gitlab_objective_labels}")
#         test_service = ObjectiveService()
# try:
#             # Test create
#             new_obj_data = ObjectiveCreateRequest(
#                 obj_number=101,
#                 title="Test New Objective from Service",
#                 description="This is a detailed description for the new test objective."
#             )
# print(f"Attempting to create objective: {new_obj_data.title}")
#             created_objective = test_service.create_objective(new_obj_data)
# print(f"Created objective: IID {created_objective.id}, Title: {created_objective.title}, URL: {created_objective.web_url}")
#
#             # Test get
# print(f"\nAttempting to retrieve objective IID {created_objective.id}")
#             retrieved_objective = test_service.get_objective(created_objective.id)
# print(f"Retrieved objective: IID {retrieved_objective.id}, Title: {retrieved_objective.title}")
#
#             # Test list
# print("\nAttempting to list objectives...")
#             objectives = test_service.list_objectives()
# if objectives:
# print(f"Found {len(objectives)} objectives:")
#                 for obj in objectives:
# print(f"  - IID {obj.id}: {obj.title}")
# else:
# print("No objectives found or error listing them.")
#
# except Exception as e:
# print(f"An error occurred during ObjectiveService testing: {e}")
# print("Please ensure your .env file is correctly set up and the GitLab project/token are valid.")

# To run this __main__ block for testing:
# 1. Ensure app/services/__init__.py exports gitlab_service instance.
# 2. Create a .env file in the project root:
#    GITLAB_API_URL="https://gitlab.com" (or your instance)
#    GITLAB_ACCESS_TOKEN="your_gitlab_access_token"
#    GITLAB_PROJECT_ID="your_gitlab_project_id"
#    GITLAB_OBJECTIVE_LABELS="Objective" (or your chosen label(s), comma-separated if multiple)
# 3. Install dependencies: pip install python-gitlab pydantic pydantic-settings
# 4. Run from the project root: python app/services/objective_service.py
#
# Note: The print statements in GitlabService will also output, helping trace calls.
# This isolated test doesn't involve the FastAPI app itself.
