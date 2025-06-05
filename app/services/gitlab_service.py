import gitlab
from gitlab.v4.objects import ProjectIssue, ProjectIssueLink, Project
from app.config import settings
from typing import List

class GitlabService:
    def __init__(self):
        try:
            self.gl = gitlab.Gitlab(settings.gitlab_api_url, private_token=settings.gitlab_access_token, ssl_verify=False)
            self.gl.auth()
            # print("Successfully authenticated with GitLab.") # Reduced verbosity for non-interactive use
        except gitlab.exceptions.GitlabAuthenticationError as e:
            # print(f"GitLab Authentication Error: {e}. Please check your GITLAB_API_URL and GITLAB_ACCESS_TOKEN.")
            raise
        except Exception as e:
            # print(f"An error occurred during GitLab client initialization: {e}")
            raise
        self._project = None

    def get_project(self) -> Project:
        if self._project is None:
            try:
                self._project = self.gl.projects.get(settings.gitlab_project_id)
                # print(f"Successfully fetched project: {self._project.name}")
            except gitlab.exceptions.GitlabGetError as e:
                # print(f"Error getting project {settings.gitlab_project_id}: {e}")
                raise
            except Exception as e:
                # print(f"An unexpected error occurred while fetching project {settings.gitlab_project_id}: {e}")
                raise
        return self._project

    def create_issue(self, title: str, description: str, labels: List[str] = None) -> ProjectIssue:
        project = self.get_project()
        if labels is None:
            labels = []
        try:
            issue_data = {
                'title': title,
                'description': description,
                'labels': labels
            }
            issue = project.issues.create(issue_data)
            # print(f"Successfully created issue '{title}' with IID {issue.iid}")
            return issue
        except gitlab.exceptions.GitlabCreateError as e:
            # print(f"Error creating issue '{title}': {e}")
            raise
        except Exception as e:
            # print(f"An unexpected error occurred while creating issue '{title}': {e}")
            raise

    def get_issue(self, issue_iid: int) -> ProjectIssue:
        project = self.get_project()
        try:
            issue = project.issues.get(issue_iid)
            # print(f"Successfully fetched issue with IID {issue_iid}")
            return issue
        except gitlab.exceptions.GitlabGetError as e:
            # print(f"Error getting issue with IID {issue_iid}: {e}")
            raise # Re-raise to be handled by service layer
        except Exception as e:
            # print(f"An unexpected error occurred while getting issue IID {issue_iid}: {e}")
            raise

    def update_issue(self, issue_iid: int, title: str = None, description: str = None, labels: List[str] = None) -> ProjectIssue:
        project = self.get_project()
        try:
            issue = project.issues.get(issue_iid)

            # update_data = {} # Not used with issue.save() pattern
            if title is not None: issue.title = title
            if description is not None: issue.description = description
            if labels is not None: issue.labels = labels # This overwrites existing labels

            # Check if any attribute was actually changed before saving
            # However, issue.save() is often idempotent if no changes were made to tracked fields.
            # For simplicity, we'll call save if any parameter was provided.
            if title is None and description is None and labels is None:
                # print(f"No updates specified for issue IID {issue_iid}.")
                return issue

            issue.save()

            # Re-fetch to ensure we have the very latest state (GitLab API might have processed changes)
            updated_issue = project.issues.get(issue_iid)
            # print(f"Successfully updated issue IID {issue_iid}.")
            return updated_issue
        except gitlab.exceptions.GitlabGetError as e:
            # print(f"Error getting issue IID {issue_iid} for update: {e}")
            raise
        except gitlab.exceptions.GitlabUpdateError as e:
            # print(f"Error updating issue IID {issue_iid}: {e}")
            raise
        except gitlab.exceptions.GitlabHttpError as e:
            # print(f"Gitlab HTTP error updating issue IID {issue_iid}: {e}")
            raise
        except Exception as e:
            # print(f"An unexpected error occurred while updating issue IID {issue_iid}: {e}")
            raise

    def link_issues(self, source_issue_iid: int, target_issue_iid: int) -> ProjectIssueLink:
        project = self.get_project()
        try:
            source_issue = project.issues.get(source_issue_iid)
            link = source_issue.links.create({
                'target_project_id': project.id,
                'target_issue_iid': target_issue_iid
            })
            # print(f"Successfully linked issue IID {target_issue_iid} to issue IID {source_issue_iid}")
            return link
        except gitlab.exceptions.GitlabGetError as e: # If source_issue_iid is not found
            # print(f"Error getting source issue IID {source_issue_iid} for linking: {e}")
            raise
        except gitlab.exceptions.GitlabCreateError as e: # If linking fails (e.g., target_issue_iid not found)
            # print(f"Error linking issue IID {target_issue_iid} to IID {source_issue_iid}: {e}")
            raise
        except Exception as e:
            # print(f"An unexpected error occurred while linking issues {source_issue_iid} and {target_issue_iid}: {e}")
            raise

    def list_issues(self, labels: List[str] = None):
        project = self.get_project()
        try:
            params = {'all': True}
            if labels:
                params['labels'] = labels
            issues = project.issues.list(**params)
            # print(f"Found {len(issues)} issues" + (f" with labels {labels}." if labels else "."))
            return issues
        except gitlab.exceptions.GitlabListError as e:
            # print(f"Error listing issues: {e}")
            raise
        except Exception as e:
            # print(f"An unexpected error occurred while listing issues: {e}")
            raise

gitlab_service = GitlabService()
