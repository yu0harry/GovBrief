from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Public Document AI"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"]
    )
    
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_DEFAULT: str = "gpt-4o-mini"
    OPENAI_MODEL_PREMIUM: str = "gpt-4o"

    GOOGLE_API_KEY: str = ""

    UPLOAD_DIR: str = "./tmp/uploads"
    MAX_FILE_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".hwp", ".docx", ".jpg", ".jpeg", ".png"]
    )
    
    CACHE_TTL: int = 86400
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def validate_settings():
    errors = []
    
    if not settings.PROJECT_NAME:
        errors.append("PROJECT_NAME이 설정되지 않았습니다.")
    
    if not settings.UPLOAD_DIR:
        errors.append("UPLOAD_DIR이 설정되지 않았습니다.")
    
    if errors:
        raise ValueError("\n".join(errors))
    
    return True


if __name__ == "__main__":
    print("=== 설정 확인 ===")
    print(f"프로젝트명: {settings.PROJECT_NAME}")
    print(f"API 버전: {settings.API_V1_STR}")
    print(f"디버그 모드: {settings.DEBUG}")
    print(f"허용된 Origin: {settings.ALLOWED_ORIGINS}")
    print(f"업로드 디렉토리: {settings.UPLOAD_DIR}")
    print(f"최대 파일 크기: {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
    print(f"허용된 확장자: {settings.ALLOWED_EXTENSIONS}")
    print("\n✅ 설정 로드 완료!")