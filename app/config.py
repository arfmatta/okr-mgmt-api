from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any # Optional is implicitly handled by Any for validator
from pydantic import field_validator

class Settings(BaseSettings):
    gitlab_api_url: str = "https://gitlab.com"
    gitlab_access_token: str
    gitlab_project_id: str

    gitlab_objective_labels: List[str] = []
    gitlab_kr_labels: List[str] = []

    @field_validator('gitlab_objective_labels', 'gitlab_kr_labels', mode='before')
    @classmethod
    def _parse_comma_separated_list_robust(cls, v: Any) -> List[str]:
        if not isinstance(v, str):
            return [] # Not a string, return empty list

        processed_v = v.strip() # Remove leading/trailing whitespace from the whole string

        # Check if the string is quoted (e.g., "label1,label2") and strip quotes
        if processed_v.startswith('"') and processed_v.endswith('"'):
            processed_v = processed_v[1:-1]

        if not processed_v: # If string is empty after stripping quotes and whitespace
            return []

        # Split by comma, strip whitespace from each item, and filter out empty strings
        labels = [label.strip() for label in processed_v.split(',') if label.strip()]
        return labels

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()

# For local debugging:
# if __name__ == '__main__':
#     # Create a dummy .env for testing this script directly
#     with open(".env_test_config", "w") as f:
#         f.write('GITLAB_API_URL="https://test.gitlab.com"\n')
#         f.write('GITLAB_ACCESS_TOKEN="test_token"\n')
#         f.write('GITLAB_PROJECT_ID="123"\n')
#         f.write('GITLAB_OBJECTIVE_LABELS=" Label Foo , Label Bar "\n') # Unquoted with spaces
#         f.write('GITLAB_KR_LABELS=""\n') # Empty string
#         # f.write('GITLAB_OBJECTIVE_LABELS_QUOTED=""2025,OKR SUTI,OKR::Objetivo,OKR::Q2""\n') # Test quoted

#     class TestSettings(BaseSettings):
#         gitlab_api_url: str = "https://gitlab.com"
#         gitlab_access_token: str
#         gitlab_project_id: str
#         gitlab_objective_labels: List[str] = []
#         gitlab_kr_labels: List[str] = []
#         # gitlab_objective_labels_quoted: List[str] = Field(default=[], validation_alias=AliasChoices('GITLAB_OBJECTIVE_LABELS_QUOTED', 'DOES_NOT_EXIST'))


#         @field_validator('gitlab_objective_labels', 'gitlab_kr_labels', mode='before') # Removed 'gitlab_objective_labels_quoted' for simplicity
#         @classmethod
#         def _parse_comma_separated_list_robust(cls, v: Any) -> List[str]:
#             if not isinstance(v, str): return []
#             processed_v = v.strip()
#             if processed_v.startswith('"') and processed_v.endswith('"'):
#                 processed_v = processed_v[1:-1]
#             if not processed_v: return []
#             return [label.strip() for label in processed_v.split(',') if label.strip()]

#         model_config = SettingsConfigDict(env_file=".env_test_config", extra='ignore')

#     test_settings_instance = TestSettings() # Renamed variable
#     print(f"Objective Labels: {test_settings_instance.gitlab_objective_labels}")
#     print(f"KR Labels: {test_settings_instance.gitlab_kr_labels}")
#     # print(f"Objective Labels Quoted: {test_settings.gitlab_objective_labels_quoted}")

#     import os
#     os.remove(".env_test_config")
