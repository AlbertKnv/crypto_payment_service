from base64 import urlsafe_b64encode
from hashlib import md5

from pydantic import BaseSettings, AnyUrl, AnyHttpUrl, PostgresDsn, Field
from cryptography.fernet import Fernet


class InitialSettings(BaseSettings):
    SECRET_KEY: str = Field(..., min_length=16)


init_settings = InitialSettings()


class Settings(InitialSettings):
    TESTNET: bool
    DATABASE_URI: PostgresDsn
    REDIS_HOST: str
    CALLBACK_URL: AnyHttpUrl
    CIPHER: Fernet = Fernet(urlsafe_b64encode(
        md5(init_settings.SECRET_KEY.encode()).hexdigest()[:32].encode()
    ))
    RPC_PROVIDER: AnyHttpUrl
    RPC_USER: str
    RPC_PASSWORD: str
    ZMQ_SOCKET: AnyUrl
    ADDRESS: str


settings = Settings()
