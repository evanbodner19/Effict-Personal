from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_refresh_token: str = ""
    canvas_ical_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
