import json
import os
from pathlib import Path

DEFAULT_SETTINGS = {
    "app_name": "OSCAL Compliance Suite",
    "default_actor": "M. Muster",
    "review_workflow": ["review_required", "approved", "rejected"],
    "target_scopes": [
        "IT-Betrieb GmbH",
        "IT-Sicherheit",
        "Produktionsnetzwerk OT",
        "Zentrale Verwaltung",
    ],
    "catalog_sources": ["NIS2", "ISO 27001", "BSI IT-Grundschutz", "CUSTOM"],
    "allowed_statuses": ["open", "partial", "fulfilled", "na"],
}


def get_settings_path() -> str:
    env_path = os.getenv("TOOL_SETTINGS_PATH")
    if env_path:
        return env_path
    return str(Path(__file__).resolve().parent.parent / "tool_settings.json")


def get_settings(path: str | None = None) -> dict:
    settings_path = path or get_settings_path()
    try:
        with open(settings_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for key, value in DEFAULT_SETTINGS.items():
            data.setdefault(key, value)
        return data
    except FileNotFoundError:
        save_settings(DEFAULT_SETTINGS, path=settings_path)
        return DEFAULT_SETTINGS.copy()


def save_settings(data: dict, path: str | None = None) -> dict:
    settings_path = path or get_settings_path()
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    Path(settings_path).parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    return merged
