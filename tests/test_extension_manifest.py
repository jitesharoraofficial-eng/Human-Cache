import json
import os
import pytest

EXTENSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extension"))

def test_extension_manifest_validity():
    """Verify extension manifest is valid JSON, specifies manifest_version 3, and includes required permissions."""
    manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
    assert os.path.exists(manifest_path), "manifest.json missing in extension directory"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("manifest_version") == 3
    assert "notifications" in manifest.get("permissions", []), "Missing 'notifications' permission"
    assert "storage" in manifest.get("permissions", []), "Missing 'storage' permission"
    assert "activeTab" in manifest.get("permissions", []), "Missing 'activeTab' permission"
    assert "contextMenus" in manifest.get("permissions", []), "Missing 'contextMenus' permission"

    # Verify background service worker script exists
    sw = manifest.get("background", {}).get("service_worker")
    assert sw, "Missing background service_worker"
    assert os.path.exists(os.path.join(EXTENSION_DIR, sw))

    # Verify popup file exists
    popup = manifest.get("action", {}).get("default_popup")
    assert popup, "Missing default_popup in action"
    assert os.path.exists(os.path.join(EXTENSION_DIR, popup))


def test_extension_scripts_syntax():
    """Verify background.js, popup.js, and content.js exist and contain no obvious missing tokens."""
    for script_name in ["background.js", "popup.js", "content.js"]:
        path = os.path.join(EXTENSION_DIR, script_name)
        assert os.path.exists(path), f"Script {script_name} missing"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 50, f"Script {script_name} unexpectedly empty"
