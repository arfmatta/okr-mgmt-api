import re
import gitlab # For gitlab client and exceptions
from typing import List, Optional
from app.services.gitlab_service import gitlab_service # Correct import
from app.models import KRCreateRequest, KRResponse, KRUpdateRequest
from app.config import settings
from gitlab.v4.objects import ProjectIssue
# For gitlab.exceptions -> already imported with `import gitlab`

class KRService:
    def __init__(self):
        self.gitlab_service = gitlab_service # Correct assignment
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
            kr_title = f"**{objective_prefix} - KR{kr_data.kr_number}**: {kr_data.title}"
            kr_reference_line = f"- [ ] {kr_title} ~\"{self.kr_reference_label}\""

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

    # Method to be placed inside KRService class:
    def update_kr(self, kr_iid: int, kr_data_input: KRUpdateRequest) -> KRResponse:
        try:
            issue = self.gitlab_service.get_issue(kr_iid)
        except gitlab.exceptions.GitlabGetError:
            raise ValueError(f"KR with IID {kr_iid} not found.")

        current_description = issue.description or ""
        updates = kr_data_input.model_dump(exclude_unset=True)

        # --- Determine new values, falling back to current if not provided ---

        # 1. Quoted Description
        current_quoted_desc_match = re.search(r"### Descrição\s*((?:> .*(?:\n|$))+)", current_description, re.MULTILINE)
        current_quoted_desc_content = ""
        if current_quoted_desc_match:
            lines = current_quoted_desc_match.group(1).strip().split('\n')
            current_quoted_desc_content = "\n".join([line[2:] if line.startswith("> ") else line for line in lines])

        final_description_content = updates.get("description", current_quoted_desc_content)
        if "description" in updates and not final_description_content.strip(): # Specifically check if update was to empty
            final_quoted_description_block = "> (Descrição não fornecida)"
        elif final_description_content.strip():
            final_quoted_description_block = "\n".join([f"> {line}" for line in final_description_content.splitlines()])
        else: # Fallback to current or default if current was also empty
            final_quoted_description_block = "> (Descrição não fornecida)"


        # 2. Meta Prevista
        meta_prevista_match = re.search(r"\*\*Meta prevista\*\*: ([\d\.]+)\s*%", current_description)
        current_meta_prevista = int(float(meta_prevista_match.group(1))) if meta_prevista_match else 0
        final_meta_prevista = updates.get("meta_prevista", current_meta_prevista)

        # 3. Meta Realizada
        meta_realizada_match = re.search(r"\*\*Meta realizada\*\*: ([\d\.]+)\s*%", current_description)
        current_meta_realizada = int(float(meta_realizada_match.group(1))) if meta_realizada_match else 0
        final_meta_realizada = updates.get("meta_realizada", current_meta_realizada)

        # 4. Responsáveis
        responsaveis_match = re.search(r"\*\*Responsável\(eis\)\*\*: ([^\n]+)", current_description)
        current_responsaveis_str = responsaveis_match.group(1).strip() if responsaveis_match else "N/A"

        if "responsaveis" in updates:
            final_responsaveis_str = ", ".join(updates["responsaveis"]) if updates["responsaveis"] else "N/A"
        else:
            final_responsaveis_str = current_responsaveis_str

        # --- Preserve Activities Table ---
        activities_table_header_default = "| Projetos/Ações/Atividades | Partes interessadas | Prazo Previsto | Prazo Realizado | % Previsto | % Realizado |"
        activities_table_separator_default = "|---------------------------|----------------------|----------------|-----------------|------------|-------------|"

        activities_table_str = ""

        header_search_match = re.search(re.escape(activities_table_header_default), current_description, re.IGNORECASE)
        if header_search_match:
            table_start_index = header_search_match.start()
            activities_table_str = current_description[table_start_index:]
            activities_table_str = activities_table_str.replace('\r\n', '\n') # Normalize newlines
        else:
            activities_table_str = f"{activities_table_header_default}\n{activities_table_separator_default}"

        # --- Reconstruct Description ---
        description_parts = [
            "### Descrição",
            "",
            final_quoted_description_block,
            "",
            f"**Meta prevista**: {final_meta_prevista}%  ",
            f"**Meta realizada**: {final_meta_realizada}%  ",
            f"**Responsável(eis)**: {final_responsaveis_str}  ",
            "",
            activities_table_str.strip()
        ]

        new_full_description = "\n".join(description_parts) # Use '\n' for join
        new_full_description = re.sub(r'\n{3,}', '\n\n', new_full_description).strip() # Use '\n'

        updated_issue = self.gitlab_service.update_issue(
            issue_iid=kr_iid, description=new_full_description
        )

        objective_iid_for_response = None
        return self._map_issue_to_kr_response(updated_issue, objective_iid_for_response)

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
