from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(dotenv_path=".env", override=True)


class Settings(BaseSettings):
    DEV_MODE: bool

    SENTRY_DSN: str

    POSTGRES_DB_HOST: str
    POSTGRES_DB_PORT: int
    POSTGRES_DB_USER: str
    POSTGRES_DB_PASS: str
    POSTGRES_DB_NAME: str

    TEST_POSTGRES_DB_HOST: str
    TEST_POSTGRES_DB_PORT: int
    TEST_POSTGRES_DB_USER: str
    TEST_POSTGRES_DB_PASS: str
    TEST_POSTGRES_DB_NAME: str

    MONGO_DB_HOST: str
    MONGO_DB_PORT: int
    MONGO_DB_USER: str
    MONGO_DB_PASS: str
    MONGO_DB_NAME: str

    MYSQL_DB_HOST: str
    MYSQL_DB_PORT: int
    MYSQL_DB_USER: str
    MYSQL_DB_PASS: str
    MYSQL_DB_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASS: str
    REDIS_DB_REVOKE_TOKENS: int
    REDIS_DB_CACHE: int
    REDIS_DB_CELERY_BROKER: int
    REDIS_DB_CELERY_RESULT: int
    REDIS_DB_CELERY_REDBEAT: int
    REDIS_DB_LIMITER: int

    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASS: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    USE_CREDENTIALS: bool
    VALIDATE_CERTS: bool

    API_DOMAIN: str
    TRUSTED_HOST: str
    FRONTEND_DOMAIN: str
    TRUSTED_ORIGIN: str

    LOGGING_CLIENT_ERRORS: bool
    LOGGING_REQUESTS: bool

    LOGS_PATH: str
    MEDIA_PATH: str

    YANDEX_STORAGE_KEY: str
    YANDEX_STORAGE_SECRET_KEY: str
    YANDEX_STORAGE_BUCKET: str

    GOOGLE_OAUTH2_CLIENT_ID: str
    GOOGLE_OAUTH2_CLIENT_SECRET: str
    GOOGLE_OAUTH2_REDIRECT_URI: str

    PATH_VIDEO_STREAM: str

    BOOTSTRAP_ADMIN_USERNAME: str = "danya"

    PIN_ORIGINAL_URL_TTL_SECONDS: int = 300
    PIN_MEDIA_SIGNING_SECRET: str | None = None

    MP_ELIGIBILITY_MIN_PINS: int = 5
    MP_ELIGIBILITY_MIN_VIEWS: int = 100
    MP_ELIGIBILITY_MIN_FOLLOWERS: int = 10
    MP_PLATFORM_COMMISSION_PERCENT: float = 0.0
    MP_ORDER_PENDING_TTL_MINUTES: int = 30
    MP_USD_TO_VND_RATE: float = 25000.0
    # Default False — enable only with DEV_MODE for local smoke.
    MP_SEPAY_MOCK: bool = False
    MP_SEPAY_WEBHOOK_SECRET: str | None = None
    MP_SEPAY_PAYMENT_BASE_URL: str | None = None
    # VietinBank API Banking (SePay): memo MUST start with SEVQR or bank push is dropped.
    # Empty disables prefix. Example: "SEVQR DH0B5229A353CA".
    MP_SEPAY_TRANSFER_CONTENT_PREFIX: str = "SEVQR"
    # Platform receiving account (buyer transfers here — Solution 2 lite)
    MP_PLATFORM_BANK_BIN: str | None = None  # VietQR BIN, e.g. 970415 VietinBank
    MP_PLATFORM_BANK_NAME: str | None = None
    MP_PLATFORM_ACCOUNT_NUMBER: str | None = None
    MP_PLATFORM_ACCOUNT_NAME: str | None = None
    MP_ATTESTATION_VERSION: str = "seller-rights-v1"
    MP_COPYRIGHT_REPORT_MAX: int = 5
    MP_COPYRIGHT_REPORT_WINDOW_SECONDS: int = 3600
    # Seller payout: manual | stub | open_api (open_api raises NotConfigured — no HTTP)
    MP_PAYOUT_PROVIDER: str = "manual"

    @property
    def RABBITMQ_URL_BROKER(self):
        return f"pyamqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    @property
    def RABBITMQ_URL_RESULT(self):
        return f"rpc://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    @property
    def MYSQL_URL_ASYNC(self):
        return f"mysql+aiomysql://{self.MYSQL_DB_USER}:{self.MYSQL_DB_PASS}@{self.MYSQL_DB_HOST}:{self.MYSQL_DB_PORT}/{self.MYSQL_DB_NAME}"

    @property
    def MONGO_URL(self):
        return f"mongodb://{self.MONGO_DB_USER}:{self.MONGO_DB_PASS}@{self.MONGO_DB_HOST}:{self.MONGO_DB_PORT}/{self.MONGO_DB_NAME}?authSource=admin"

    @property
    def REDIS_URL_CELERY_REDBEAT(self):
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_REDBEAT}"

    @property
    def REDIS_URL_CELERY_BROKER(self):
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_BROKER}"

    @property
    def REDIS_URL_CELERY_RESULT(self):
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_RESULT}"

    @property
    def REDIS_URL_REVOKE_TOKENS(self):
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_REVOKE_TOKENS}"

    @property
    def REDIS_URL_CACHE(self):
        return (
            f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CACHE}"
        )

    @property
    def REDIS_URL_LIMITER(self):
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_LIMITER}"

    @property
    def POSTGRES_URL_ASYNC(self):
        return f"postgresql+asyncpg://{self.POSTGRES_DB_USER}:{self.POSTGRES_DB_PASS}@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB_NAME}"

    @property
    def TEST_POSTGRES_URL_ASYNC(self):
        return f"postgresql+asyncpg://{self.TEST_POSTGRES_DB_USER}:{self.TEST_POSTGRES_DB_PASS}@{self.TEST_POSTGRES_DB_HOST}:{self.TEST_POSTGRES_DB_PORT}/{self.TEST_POSTGRES_DB_NAME}"

    @property
    def POSTGRES_URL_SYNC(self):
        return f"postgresql://{self.POSTGRES_DB_USER}:{self.POSTGRES_DB_PASS}@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings: Settings = Settings()
