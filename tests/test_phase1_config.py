import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def contrast(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize(("mode", "accent"), [("light", "#801F3F"), ("dark", "#B84868")])
def test_dual_theme_and_main_contrast(mode, accent):
    theme = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())["theme"]
    assert theme["base"] == "light"
    colors = theme[mode]
    assert colors["primaryColor"] == accent
    assert contrast("#FFFFFF", accent) >= 4.5
    for area in (colors, colors["sidebar"]):
        for background in (area["backgroundColor"], area["secondaryBackgroundColor"]):
            assert contrast(area["textColor"], background) >= 4.5
            assert contrast(area["borderColor"], background) >= 3
            assert contrast(colors["linkColor"], background) >= 4.5


def test_no_ai_menu_in_phase1():
    code = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"🧠 AI Memory"' not in code
    assert "search_memory" not in code


def test_local_settings_are_ignored():
    rules = (ROOT / ".gitignore").read_text().splitlines()
    assert ".streamlit/secrets.toml" in rules
    assert ".env" in rules
