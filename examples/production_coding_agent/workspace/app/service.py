from app.config import DEFAULT_TIMEOUT_MS, load_settings


def build_client_config(env: dict[str, str]) -> dict[str, str | int]:
    settings = load_settings(env)
    config = {
        "api_base": settings["api_base"],
        "timeout_ms": DEFAULT_TIMEOUT_MS,
    }
    if settings["api_key"]:
        config["api_key"] = settings["api_key"]
    return config
