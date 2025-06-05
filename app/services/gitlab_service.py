import gitlab
from gitlab.v4.objects import ProjectIssue, ProjectIssueLink, Project
from app.config import settings
from typing import List, Optional, Dict, Any # Updated import

class GitlabService:
    def __init__(self):
        try:
            self.gl = gitlab.Gitlab(settings.gitlab_api_url, private_token=settings.gitlab_access_token, ssl_verify=False)
            self.gl.auth()
        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise
        except Exception as e:
            raise
        self._project: Optional[Project] = None

    def get_project(self) -> Project:
        if self._project is None:
            try:
                self._project = self.gl.projects.get(settings.gitlab_project_id)
            except gitlab.exceptions.GitlabGetError as e:
                raise
            except Exception as e:
                raise
        # Re-instated explicit check as per setup script for this subtask
        if self._project is None:
            raise Exception(f"GitLab project with ID {settings.gitlab_project_id} not found or failed to fetch.")
        return self._project

    def create_issue(self, title: str, description: str, labels: Optional[List[str]] = None) -> ProjectIssue:
        project = self.get_project()
        issue_labels: List[str] = labels if labels is not None else []
        try:
            issue_data = {
                'title': title,
                'description': description,
                'labels': issue_labels
            }
            issue = project.issues.create(issue_data)
            return issue
        except gitlab.exceptions.GitlabCreateError as e:
            raise
        except Exception as e:
            raise

    def get_issue(self, issue_iid: int) -> ProjectIssue:
        project = self.get_project()
        try:
            issue = project.issues.get(issue_iid)
            return issue
        except gitlab.exceptions.GitlabGetError as e:
            raise
        except Exception as e:
            raise

    def update_issue(self, issue_iid: int, title: Optional[str] = None, description: Optional[str] = None, labels: Optional[List[str]] = None) -> ProjectIssue:
        project = self.get_project()
        try:
            issue = project.issues.get(issue_iid)

            made_changes = False
            if title is not None:
                issue.title = title
                made_changes = True
            if description is not None:
                issue.description = description
                made_changes = True
            if labels is not None:
                issue.labels = labels
                made_changes = True

            if not made_changes:
                return issue

            issue.save()

            updated_issue = project.issues.get(issue_iid)
            return updated_issue
        except gitlab.exceptions.GitlabGetError as e:
            raise
        except gitlab.exceptions.GitlabUpdateError as e:
            raise
        except gitlab.exceptions.GitlabHttpError as e:
            raise
        except Exception as e:
            raise

    def link_issues(self, source_issue_iid: int, target_issue_iid: int) -> ProjectIssueLink:
        project = self.get_project()
        try:
            source_issue = project.issues.get(source_issue_iid)
            link = source_issue.links.create({
                'target_project_id': project.id,
                'target_issue_iid': target_issue_iid
            })
            return link
        except gitlab.exceptions.GitlabGetError as e:
            raise
        except gitlab.exceptions.GitlabCreateError as e:
            raise
        except Exception as e:
            raise

    def list_issues(self, labels: Optional[List[str]] = None) -> List[ProjectIssue]:
        project = self.get_project()
        try:
            # Corrected type hint for params
            params: Dict[str, Any] = {'all': True}
            if labels:
                params['labels'] = labels

            issues_raw = project.issues.list(**params)
            issues: List[ProjectIssue] = issues_raw
            return issues
        except gitlab.exceptions.GitlabListError as e:
            raise
        except Exception as e:
            raise

gitlab_service = GitlabService()
