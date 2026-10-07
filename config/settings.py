from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TilMaroon2 API"
    app_version: str = "0.1.0"
    debug: bool = False


    database_url: SecretStr = Field(min_length=1, description="URL de conexão fornecida pelo ambiente.")
    database_echo: bool = False


    secret_key: SecretStr = Field(description="Chave JWT aleatória de pelo menos 32 bytes.")
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expire_minutes: int = Field(default=60, gt=0)


    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret.encode("utf-8")) < 32 or "change-me" in secret.lower():
            raise ValueError("SECRET_KEY deve ser aleatória e ter pelo menos 32 bytes")
        return value


    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        description="Hosts permitidos pelo TrustedHostMiddleware.",
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="URL base do frontend em desenvolvimento. Usada para alinhar o CORS com o app Next.js.",
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        description="Origens permitidas pelo CORS em desenvolvimento e homologação.",
    )
    force_https_redirect: bool = Field(
        default=False,
        description="Redireciona requisições HTTP para HTTPS quando a aplicação estiver em produção.",
    )


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_parse_delimiter=",",
    )




settings = Settings()  # type: ignore[call-arg]  # Values come from the environment.
