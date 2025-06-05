import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Dict, Any # Adicionado Dict
from pydantic import Field, model_validator

# Configurar logging básico para ver as mensagens no console
logging.basicConfig(level=logging.INFO) # Pode mudar para logging.DEBUG para mais detalhes se necessário
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    gitlab_api_url: str = "https://gitlab.com"
    gitlab_access_token: str
    gitlab_project_id: str
    
    # Campos para ler as strings brutas do .env
    # Usamos alias para mapear para os nomes das variáveis de ambiente
    GITLAB_OBJECTIVE_LABELS_STR: Optional[str] = Field(None, alias="GITLAB_OBJECTIVE_LABELS")
    GITLAB_KR_LABELS_STR: Optional[str] = Field(None, alias="GITLAB_KR_LABELS")

    # Campos finais que serão List[str]
    gitlab_objective_labels: List[str] = Field(default_factory=list, exclude=True) # exclude=True para não esperar no .env
    gitlab_kr_labels: List[str] = Field(default_factory=list, exclude=True)      # exclude=True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore' 
    )

settings: Settings = Settings()

logger.info(f"Final settings loaded: Objective Labels = {settings.gitlab_objective_labels}")
logger.info(f"Final settings loaded: KR Labels = {settings.gitlab_kr_labels}")
