from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ECC_", extra="ignore")

    service_name: str = "d94-ecc"
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
    ayaan_base_url: str = "http://gateway-cloud-gateway-1:10001/tsh/api/v1/ayaan"
    ayaan_token: str = ""

    @property
    def allowed_user_ids(self) -> set[int]:
        ids = self.telegram_allowed_user_ids.split(",")
        return {int(v.strip()) for v in ids if v.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

