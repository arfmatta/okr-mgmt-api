from app.services import gitlab_service
from app.models import ObjectiveCreateRequest, ObjectiveResponse, KRDetailResponse # Removed GitlabConfig as it's not used
from app.config import settings
from gitlab.v4.objects import ProjectIssue, ProjectIssueLink
from typing import List, Optional # Ensure List is imported
import re

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

    def get_krs_for_objective(self, objective_iid: int) -> List[KRDetailResponse]:
        krs_list: List[KRDetailResponse] = []
        try:
            objective_issue = self.gitlab_service.get_issue(objective_iid)
            # .links.list() returns ProjectIssueLink items, but these items ARE the linked issues themselves,
            # not just link descriptors.
            # However, they might be lightweight representations.
            # To be safe and ensure all fields like 'description' are fully populated,
            # we fetch each linked issue again using its IID.
            linked_issue_references = objective_issue.links.list()


            for linked_issue_ref in linked_issue_references:
                # The 'source_issue_iid' and 'target_issue_iid' on the ProjectIssueLink object
                # tell us which issue was the source and which was the target of the link action.
                # When a KR is created, it (source) links to an Objective (target).
                # objective_issue.links.list() gives us the KR issues directly.
                # So, linked_issue_ref.iid should be the KR's IID.

                # Fetch the full issue details for the KR candidate
                kr_candidate_issue = self.gitlab_service.get_issue(linked_issue_ref.iid)

                if "OKR::Resultado Chave" not in kr_candidate_issue.labels:
                    continue

                # Parse KR data
                kr_id = kr_candidate_issue.iid
                kr_web_url = kr_candidate_issue.web_url

                kr_title_full = kr_candidate_issue.title
                kr_number_match = re.search(r"- KR(\d+):", kr_title_full)
                kr_number = int(kr_number_match.group(1)) if kr_number_match else 0

                title_match = re.search(r":\s*(.*)", kr_title_full)
                title = title_match.group(1).strip() if title_match else kr_title_full

                team_label = "N/A"
                product_label = "N/A"
                for label_str in kr_candidate_issue.labels:
                    if label_str.startswith("TEAM::"):
                        team_label = label_str.split("::", 1)[1]
                    elif label_str.startswith("PRODUCT::"):
                        product_label = label_str.split("::", 1)[1]

                issue_description = kr_candidate_issue.description or ""

                # Using the suggested regex for multiline quoted description
                desc_match = re.search(r"### Descrição\s*\n\n((?:> .*(?:\n|$))+)", issue_description, re.MULTILINE)
                if desc_match:
                    # Process group(1) to remove '>' and join lines
                    description_lines = desc_match.group(1).strip().split('\n')
                    processed_lines = [line[2:].strip() if line.startswith("> ") else line.strip() for line in description_lines]
                    # Further clean up by removing empty lines that might result from ">" only lines
                    # And then join with <br> for HTML like display if needed, or just \n.
                    # The model expects a simple string, so \n is better.
                    description = "\n".join(filter(None, processed_lines))

                else:
                    # Fallback if the primary regex fails - try the original simpler one
                    main_description_match_fallback = re.search(r"### Descrição\s*>\s*([^#]*)", issue_description, re.DOTALL)
                    if main_description_match_fallback:
                        description = main_description_match_fallback.group(1).strip().replace('> ', '').replace('\n', ' ') # Simpler fallback
                    else:
                        description = "N/A"


                meta_prevista_match = re.search(r"\*\*Meta prevista\*\*:\s*(\d+)%", issue_description)
                meta_prevista = int(meta_prevista_match.group(1)) if meta_prevista_match else 0

                meta_realizada_match = re.search(r"\*\*Meta realizada\*\*:\s*(\d+)%", issue_description)
                meta_realizada = int(meta_realizada_match.group(1)) if meta_realizada_match else 0

                responsaveis_match = re.search(r"\*\*Responsável\(eis\)\*\*:\s*([^\n]+)", issue_description)
                responsaveis_str = responsaveis_match.group(1).strip() if responsaveis_match else ""
                responsaveis = [r.strip() for r in responsaveis_str.split(',') if r.strip()] if responsaveis_str else []

                krs_list.append(KRDetailResponse(
                    id=kr_id,
                    web_url=kr_web_url,
                    objective_iid=objective_iid, # This is the IID of the objective this method was called for
                    kr_number=kr_number,
                    title=title,
                    description=description,
                    meta_prevista=meta_prevista,
                    meta_realizada=meta_realizada,
                    team_label=team_label,
                    product_label=product_label,
                    responsaveis=responsaveis
                ))

            return krs_list
        except Exception as e:
            # Log the error or handle it as per application's error handling strategy
            print(f"Error getting KRs for objective {objective_iid}: {e}")
            # Depending on requirements, you might want to return an empty list or re-raise
            # For now, returning empty list on error as per typical service behavior unless it's a critical failure
            return []

    def list_objectives_by_filters(self, year: Optional[str] = None, team: Optional[str] = None, product: Optional[str] = None) -> List[ObjectiveResponse]:
        query_specific_labels: List[str] = []

        if year:
            query_specific_labels.append(year)
        if team:
            query_specific_labels.append(f"TEAM::{team}")
        if product:
            query_specific_labels.append(f"PRODUCT::{product}")

        if not query_specific_labels:
            raise ValueError("At least one filter (year, team, or product) must be provided.")

        # Combine base objective labels with specific filter labels. Using a set to ensure uniqueness.
        # self.objective_labels should already be a List[str]
        combined_labels = list(set(list(self.objective_labels) + query_specific_labels))

        try:
            issues: List[ProjectIssue] = self.gitlab_service.list_issues(labels=combined_labels)
            return [self._map_issue_to_objective_response(issue) for issue in issues]
        except ValueError as ve: # Catch the ValueError from list_issues if GitLab complains
            print(f"ValueError during GitLab issue listing: {ve}") # Or re-raise specific app error
            raise
        except Exception as e:
            print(f"Error listing objectives by filters ({year}, {team}, {product}): {e}")
            # Depending on how critical this is, you might return [] or re-raise
            raise # Re-raising for now as this indicates a more general issue


objective_service = ObjectiveService()
