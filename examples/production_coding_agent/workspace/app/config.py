DEFAULT_TIMEOUT_MS = 5000


def load_settings(env: dict[str, str]) -> dict[str, str]:
    api_base = env.get("API_BASE_URL", "")
    api_key = env.get("API_KEY", "")
    mode = env.get("APP_MODE", "dev")
    return {
        "api_base": api_base.strip(),
        "api_key": api_key.strip(),
        "mode": mode,
    }
