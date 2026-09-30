from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TilMaroon2 API"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = Field(
        default="mysql+pymysql://root:root@localhost:3306/tilmaroon2",
        description="URL de conexão com o MySQL. Ajuste usuário/senha e nome do schema conforme o ambiente.",
    )
    database_echo: bool = False

    secret_key: str = Field(
        default="change-me-in-production-tilmaroon-2026-secret-key",
        description="Chave secreta para assinar JWT. Trocar em produção.",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
