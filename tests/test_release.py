import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_compatibility_uses_stable_upper_bound():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["tool"]["bench"]["frappe-dependencies"]["frappe"] == ">=16.0.0-dev,<17.0.0"


def test_package_and_app_versions_agree():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    module = (ROOT / "wise_bank_feed/__init__.py").read_text()
    assert re.search(r'__version__\s*=\s*[\'"]' + re.escape(project["version"]) + r'[\'"]', module)
