from app.config import DEFAULT_SETTINGS, get_settings, save_settings


def test_default_settings_include_user_and_review_workflow():
    settings = get_settings()

    assert settings["app_name"] == DEFAULT_SETTINGS["app_name"]
    assert "default_actor" in settings
    assert "review_workflow" in settings
    assert "approved" in settings["review_workflow"]


def test_save_settings_persists_custom_values(tmp_path):
    custom = {
        "app_name": "NIS2 Audit Lab",
        "default_actor": "Max Tester",
        "review_workflow": ["review_required", "approved"],
        "target_scopes": ["IT-Betrieb GmbH", "HR GmbH"],
    }

    saved = save_settings(custom, path=str(tmp_path / "settings.json"))

    assert saved["default_actor"] == "Max Tester"
    assert saved["target_scopes"] == ["IT-Betrieb GmbH", "HR GmbH"]
    loaded = get_settings(path=str(tmp_path / "settings.json"))
    assert loaded["app_name"] == "NIS2 Audit Lab"
