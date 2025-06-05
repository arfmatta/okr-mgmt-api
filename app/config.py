from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Any
from pydantic import field_validator

class Settings(BaseSettings):
    gitlab_api_url: str = "https://gitlab.com"
    gitlab_access_token: str
    gitlab_project_id: str # Should be the numeric ID

    # These fields will be populated by the validator from comma-separated strings
    # The environment variables should be GITLAB_OBJECTIVE_LABELS and GITLAB_KR_LABELS
    # Pydantic BaseSettings will automatically try to match these field names
    # (case-insensitively) to environment variables.
    gitlab_objective_labels: List[str] = []
    gitlab_kr_labels: List[str] = []

    @field_validator('gitlab_objective_labels', 'gitlab_kr_labels', mode='before')
    @classmethod
    def _parse_comma_separated_list(cls, v: Any) -> List[str]:
        # This validator runs *before* Pydantic tries to validate the type as List[str].
        # 'v' is the raw value from the .env file (or None if not set/default not applicable yet).
        if isinstance(v, str):
            if v.strip(): # If the string is not empty after stripping whitespace
                # Split by comma, strip whitespace from each part, and filter out empty strings
                return [label.strip() for label in v.split(',') if label.strip()]
        # If v is None (env var not set), or an empty string, or not a string that yields valid labels,
        # return an empty list. Pydantic will then use this empty list.
        # The field default '=[]' ensures that if the env var is entirely missing and
        # this validator returns [], it's a valid List[str].
        return []

    model_config = SettingsConfigDict(
        env_file=".env",        # Load from .env file
        env_file_encoding='utf-8',
        extra='ignore',         # Ignore extra fields from .env
    )

# Create a global instance of the settings
settings = Settings()

# Optional: For debugging locally, you can print to see loaded values
# print(f"Loaded settings in config.py (refined):")
# print(f"  GITLAB_OBJECTIVE_LABELS: {settings.gitlab_objective_labels}")
# print(f"  GITLAB_KR_LABELS: {settings.gitlab_kr_labels}")
