"""Optional color themes for apicli."""

from __future__ import annotations

from textual.theme import Theme

CYBERPUNK_THEME = Theme(
    name="cyberpunk",
    primary="#00e5ff",
    secondary="#ff2a6d",
    accent="#ff2e97",
    warning="#f9f002",
    error="#ff3864",
    success="#05ffa1",
    foreground="#d7f9ff",
    background="#0b0f1a",
    surface="#12172a",
    panel="#1a2140",
    boost="#2a3666",
    dark=True,
    variables={
        "button-color-foreground": "#0b0f1a",
        "input-cursor-background": "#00e5ff",
        "input-cursor-foreground": "#0b0f1a",
        "input-selection-background": "#ff2e9740",
        "block-cursor-background": "#ff2e97",
        "block-cursor-foreground": "#0b0f1a",
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#00e5ff",
    },
)
