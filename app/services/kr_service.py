import re
from typing import List, Optional # Ensure List and Optional are imported
from app.services import gitlab_service
from app.models import KRCreateRequest, KRResponse
from app.config import settings
from gitlab.v4.objects import ProjectIssue
import gitlab # For gitlab.exceptions

class KRService:
    def __init__(self):
        self.gitlab_service = gitlab_service
        self.kr_labels: List[str] = settings.gitlab_kr_labels if settings.gitlab_kr_labels else []
        self.kr_reference_label: str = "OKR::Resultado Chave"

    def _map_issue_to_kr_response(self, issue: ProjectIssue, objective_iid: Optional[int] = None) -> KRResponse:
        return KRResponse(
            id=issue.iid,
            title=issue.title,
            description=issue.description or "",
            web_url=issue.web_url,
            objective_iid=objective_iid or 0
        )

    def _get_objective_prefix(self, objective_iid: int) -> str:
        parent_objective_issue = self.gitlab_service.get_issue(objective_iid)
        match = re.match(r"^(OBJ\d+):.*", parent_objective_issue.title)
        if match:
            return match.group(1)
        return f"OBJ{objective_iid}"

    def _format_kr_description(self, kr_data: KRCreateRequest) -> str:
        quoted_description = ""
        if kr_data.description and kr_data.description.strip(): # Check if description has content
            quoted_description = "\n".join([f"> {line}" for line in kr_data.description.splitlines()])
        else:
            quoted_description = "> (Descrição não fornecida)" # Default if empty or only whitespace

        responsaveis_list: List[str] = kr_data.responsaveis # Type hint for clarity
        responsaveis_str = ", ".join(responsaveis_list) if responsaveis_list else "N/A"

        description_parts = [
            "### Descrição",
            "",
            quoted_description,
            "",
            f"**Meta prevista**: {kr_data.meta_prevista}%  ",
            f"**Meta realizada**: {kr_data.meta_realizada}%  ",
            f"**Responsável(eis)**: {responsaveis_str}  ",
            "",
            "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |",
            "|---------------------------|----------------------|----------------|-----------------|------------|-------------|",
            "|                           |                      |                |                 |            |             |"
        ]
        return "\n".join(description_parts)

    def create_kr(self, kr_data: KRCreateRequest) -> KRResponse:
        try:
            objective_prefix = self._get_objective_prefix(kr_data.objective_iid)
        except gitlab.exceptions.GitlabGetError as e: # More specific exception
            # Consider logging the error e here
            raise ValueError(f"Parent objective with IID {kr_data.objective_iid} not found.") from e

        kr_title = f"{objective_prefix} - KR{kr_data.kr_number}: {kr_data.title}"
        kr_description = self._format_kr_description(kr_data)
        labels_to_apply: List[str] = list(set(self.kr_labels)) + [kr_data.team_label, kr_data.product_label]

        created_kr_issue = self.gitlab_service.create_issue(
            title=kr_title, description=kr_description, labels=labels_to_apply
        )

        try:
            self.gitlab_service.link_issues(
                source_issue_iid=created_kr_issue.iid, target_issue_iid=kr_data.objective_iid
            )
        except Exception as e_link:
            # Log this warning, e.g., using logging module
            print(f"Warning: Failed to link KR {created_kr_issue.iid} to Objective {kr_data.objective_iid}. Error: {e_link}")

        try:
            parent_objective_issue = self.gitlab_service.get_issue(kr_data.objective_iid)
            kr_reference_line = f"- [ ] **{kr_title}** ~\"{self.kr_reference_label}\""

            new_objective_description = parent_objective_issue.description or ""
            results_chave_heading = "### Resultados Chave"
            if results_chave_heading in new_objective_description:
                parts = new_objective_description.split(results_chave_heading, 1)
                new_objective_description = parts[0] + results_chave_heading + "\n" + kr_reference_line
                if len(parts) > 1 and parts[1].strip():
                    new_objective_description += "\n" + parts[1].strip()
                else:
                    new_objective_description += "\n"
            else:
                new_objective_description += f"\n\n{results_chave_heading}\n{kr_reference_line}\n"

            self.gitlab_service.update_issue(
                issue_iid=parent_objective_issue.iid, description=new_objective_description.strip()
            )
        except Exception as e_update_obj:
            # Log this warning
            print(f"Warning: Failed to update parent objective {kr_data.objective_iid} with KR {created_kr_issue.iid} reference. Error: {e_update_obj}")

        return self._map_issue_to_kr_response(created_kr_issue, kr_data.objective_iid)

    def get_kr(self, kr_iid: int) -> Optional[KRResponse]:
        try:
            issue = self.gitlab_service.get_issue(kr_iid)
            return self._map_issue_to_kr_response(issue, None) # Objective IID not determined here
        except gitlab.exceptions.GitlabGetError: # If KR issue itself not found
            return None # Return None as per Optional type hint
        except Exception as e:
            # Log other unexpected errors
            print(f"Error retrieving KR {kr_iid}: {e}")
            raise # Re-raise other exceptions

    def list_krs_for_objective(self, objective_iid: int) -> List[KRResponse]:
        try:
            # First, check if the parent objective exists. If not, no KRs to list.
            self.gitlab_service.get_issue(objective_iid)
        except gitlab.exceptions.GitlabGetError:
            return []

        all_krs_issues: List[ProjectIssue] = self.gitlab_service.list_issues(labels=self.kr_labels)
        linked_krs: List[KRResponse] = []
        for kr_issue_candidate in all_krs_issues:
            try:
                # For each potential KR, check its links to see if it links to the given objective_iid
                # This assumes KR is source, Objective is target as per create_kr logic.
                # If link_issues was (Objective_Source -> KR_Target), this logic would need to change
                # to iterate objective_issue.links.list() and check target_issue_iid.
                # Given create_kr links KR(source) -> Objective(target), this is complex.
                # A simpler (but less direct) way if links are "relates_to" (bidirectional):
                # Check if objective_iid is in any link associated with kr_issue_candidate.
                # The current python-gitlab might not make this super easy without knowing link IDs.

                # Let's adjust based on create_kr: KR (source) links TO Objective (target).
                # So, a KR's links will show the Objective as a target.
                # However, the link is stored ON the source. So we list links FROM the KR.
                links = kr_issue_candidate.links.list()
                for link in links:
                    # Assuming 'target_issue_iid' is an attribute on the link object from python-gitlab
                    # when listing links of an issue.
                    if hasattr(link, 'target_issue_iid') and link.target_issue_iid == objective_iid:
                        linked_krs.append(self._map_issue_to_kr_response(kr_issue_candidate, objective_iid))
                        break # Found link to the objective, no need to check other links for this KR
            except Exception as e:
                # Log error processing links for a KR candidate
                print(f"Error processing links for KR candidate {kr_issue_candidate.iid}: {e}")
        return linked_krs

    def list_all_krs(self) -> List[KRResponse]:
        try:
            issues: List[ProjectIssue] = self.gitlab_service.list_issues(labels=self.kr_labels)
            # Objective IID not determined here for simplicity
            return [self._map_issue_to_kr_response(issue) for issue in issues]
        except Exception as e:
            # Log error
            print(f"Error listing all KRs: {e}")
            raise

kr_service = KRService()
