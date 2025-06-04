from app.services import gitlab_service # Use the shared instance
from app.models import KRCreateRequest, KRResponse # Assuming models are in app.models
from app.config import settings
from gitlab.v4.objects import ProjectIssue
from typing import List, Optional

class KRService:
    def __init__(self):
        self.gitlab_service = gitlab_service
        self.kr_labels = settings.gitlab_kr_labels
        # Ensure kr_labels is a list, even if empty in settings
        if self.kr_labels is None:
            self.kr_labels = []


    def _map_issue_to_kr_response(self, issue: ProjectIssue, objective_iid: Optional[int] = None) -> KRResponse:
        """Helper to map a GitLab issue to a KRResponse model."""
        # Objective IID might not be directly on the issue object unless we parse description or find link
        # For now, if passed, we use it. Otherwise, it might need to be enriched later.
        # A more robust way would be to find the 'blocks' link to an objective.
        return KRResponse(
            id=issue.iid,
            title=issue.title,
            description=issue.description or "",
            web_url=issue.web_url,
            objective_iid=objective_iid or 0 # Placeholder, actual objective_iid needs to be determined
        )

    def create_kr(self, kr_data: KRCreateRequest) -> KRResponse:
        """
        Creates a Key Result as a GitLab issue and links it to the parent Objective.
        Description will store meta_prevista, meta_realizada, responsaveis.
        """
        title = f"KR{kr_data.kr_number}: {kr_data.title}"

        # Store structured data in the description. Markdown is a good option.
        description_parts = [
            kr_data.description,
            f"\n\n--- KR Details ---",
            f"**Meta Prevista:** {kr_data.meta_prevista}%",
            f"**Meta Realizada:** {kr_data.meta_realizada}%",
            f"**Responsáveis:** {', '.join(kr_data.responsaveis) if kr_data.responsaveis else 'N/A'}"
        ]
        full_description = "\n".join(description_parts)

        labels_to_apply = list(set(self.kr_labels))

        try:
            kr_issue = self.gitlab_service.create_issue(
                title=title,
                description=full_description,
                labels=labels_to_apply
            )

            # Link KR to its Objective
            if kr_data.objective_iid:
                self.gitlab_service.link_issues(
                    source_issue_iid=kr_data.objective_iid, # Objective is the source
                    target_issue_iid=kr_issue.iid          # KR is the target
                )
                # Note: python-gitlab link_issues creates a "relates_to" link by default.
                # For "blocks" or "is_blocked_by", you might need to specify link_type.
                # Example: self.gitlab_service.link_issues(..., link_type='blocks')
                # However, the gitlab_service.link_issues provided doesn't have link_type param yet.
                # Assuming "relates_to" is acceptable for now.

            return self._map_issue_to_kr_response(kr_issue, kr_data.objective_iid)
        except Exception as e:
            print(f"Error creating KR: {e}") # Replace with actual logging
            raise

    def get_kr(self, kr_iid: int) -> Optional[KRResponse]:
        """
        Retrieves a specific KR (GitLab issue) by its IID.
        Determining the parent objective_iid would require parsing the issue's links.
        """
        try:
            issue = self.gitlab_service.get_issue(kr_iid)
            if not issue:
                return None

            # To find the linked objective, we'd inspect issue.links or issue.related_issues()
            # This is a simplified version; a full implementation would parse links.
            # For now, we'll assume objective_iid is not easily available from just get_issue
            # and might be populated if this KR is listed as part of an objective.

            # Basic check for KR labels
            # if not all(label in issue.labels for label in self.kr_labels):
            #     print(f"Warning: Issue {kr_iid} retrieved as KR but lacks some KR labels.")

            return self._map_issue_to_kr_response(issue) # objective_iid will be 0 or None here
        except Exception as e:
            print(f"Error retrieving KR {kr_iid}: {e}") # Replace with actual logging
            raise

    def list_krs_for_objective(self, objective_iid: int) -> List[KRResponse]:
        """
        Lists all KRs linked to a specific objective.
        This requires fetching the objective, then its links, then the linked issues.
        """
        try:
            objective_issue = self.gitlab_service.get_issue(objective_iid)
            if not objective_issue:
                return []

            linked_issues = objective_issue.links.list() # Gets a list of link objects
            kr_responses: List[KRResponse] = []

            for link_info in linked_issues:
                # The link_info object tells you about the link itself.
                # We need to fetch the actual issue that is linked.
                # link_info.iid is the IID of the linked issue if using project.issue_links.list()
                # but here, objective_issue.links.list() gives links *from* the objective.
                # The target issue is what we want.
                # The attribute names might vary slightly based on python-gitlab version or how links are fetched.
                # Common attributes on a link object: source_issue_iid, target_issue_iid, link_type
                # Here, objective_issue is the source. We need the target_issue_iid.
                # This part might need adjustment based on exact link object structure.
                # Assuming link_info directly has 'iid' of the target KR issue if the link is from Objective to KR
                # Let's assume the link_info is a dict-like object from the SDK

                # A common pattern: link objects list issues *linked to* the current one.
                # So, issue_link.target_issue_iid would be the KR's IID if objective is source.
                # Or, if the link can be bidirectional, issue_link.source_issue_iid.
                # The current GitlabService.link_issues links source_issue_iid -> target_issue_iid.
                # So, if objective is source, target_issue_iid is the KR.
                # If KR is source, target_issue_iid is the objective.
                # The API for issue.links.list() returns links where the issue is the source.

                target_kr_iid = link_info.target_issue_iid # This is an assumption of the link object structure
                                                           # It might be link_info.iid or link_info.linked_issue_iid etc.
                                                           # This needs verification against actual GitLab API response / python-gitlab docs for ProjectIssueLink

                kr_issue = self.gitlab_service.get_issue(target_kr_iid) # Fetch the KR issue

                # Filter: ensure the linked issue is indeed a KR by checking its labels
                if kr_issue and all(label in kr_issue.labels for label in self.kr_labels):
                    kr_responses.append(self._map_issue_to_kr_response(kr_issue, objective_iid))

            return kr_responses
        except gitlab.exceptions.GitlabGetError as e:
            # Objective issue not found
            print(f"Objective with IID {objective_iid} not found when listing KRs: {e}")
            return []
        except Exception as e:
            print(f"Error listing KRs for objective {objective_iid}: {e}") # Replace with actual logging
            raise

    def list_all_krs(self) -> List[KRResponse]:
        """Lists all KRs based on labels, without respect to a specific objective."""
        try:
            issues = self.gitlab_service.list_issues(labels=self.kr_labels)
            # Determining objective_iid for each would require checking links for each KR,
            # which could be N+1 queries. For now, it will be unknown/0.
            return [self._map_issue_to_kr_response(issue) for issue in issues]
        except Exception as e:
            print(f"Error listing all KRs: {e}")
            raise


# Instantiate the service
kr_service = KRService()
