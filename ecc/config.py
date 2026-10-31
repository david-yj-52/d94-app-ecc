from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ECC_", extra="ignore")

    service_name: str = "d94-ecc"
    app_env: str = "local"
    bind_host: str = "0.0.0.0"
    port: int = 8080
    redis_url: str = "redis://redis:6379/0"
    api_token: str = ""
    telegram_bot_token: str = ""
    telegram_allowed_user_ids: str = ""
    nano_endpoint: str = ""
    nano_timeout_seconds: float = 30
    eureka_enabled: bool = False
    eureka_url: str = "http://eureka:8761/eureka/"
    eureka_instance_host: str = "d94-ecc"
    eureka_instance_port: int = 8080
    eureka_instance_ip: str = ""
    cli_allowlist: str = "claude,gemini,codex"
    cli_timeout_seconds: int = 1800
    cli_workspaces: str = Field(default="/workspace")
    cli_executables: str = ""
    ticket_ttl_seconds: int = 604800
    telegram_default_workspace: str = "/workspace"

    @property
    def allowed_user_ids(self) -> set[int]:
        return {int(value.strip()) for value in self.telegram_allowed_user_ids.split(",") if value.strip()}

    @property
    def allowed_clis(self) -> set[str]:
        return {value.strip().lower() for value in self.cli_allowlist.split(",") if value.strip()}

    @property
    def workspace_roots(self) -> tuple[str, ...]:
        return tuple(value.strip() for value in self.cli_workspaces.split(",") if value.strip())

    @property
    def executable_map(self) -> dict[str, str]:
        result = {}
        for pair in self.cli_executables.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                result[key.strip().lower()] = value.strip()
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()

