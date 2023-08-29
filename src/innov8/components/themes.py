import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeChangerAIO

theme_changer = ThemeChangerAIO(
    aio_id="theme",
    radio_props={
        "options": [
            {
                "label": "Cyborg",
                "value": dbc.themes.CYBORG,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Darkly",
                "value": dbc.themes.DARKLY,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Slate",
                "value": dbc.themes.SLATE,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Solar",
                "value": dbc.themes.SOLAR,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Superhero",
                "value": dbc.themes.SUPERHERO,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Vapor",
                "value": dbc.themes.VAPOR,
                "label_id": "theme-switch-label-dark",
            },
            {
                "label": "Bootstrap",
                "value": dbc.themes.BOOTSTRAP,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Flatly",
                "value": dbc.themes.FLATLY,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Journal",
                "value": dbc.themes.JOURNAL,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Lumen",
                "value": dbc.themes.LUMEN,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Minty",
                "value": dbc.themes.MINTY,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Simplex",
                "value": dbc.themes.SIMPLEX,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Spacelab",
                "value": dbc.themes.SPACELAB,
                "label_id": "theme-switch-label",
            },
            {
                "label": "United",
                "value": dbc.themes.UNITED,
                "label_id": "theme-switch-label",
            },
            {
                "label": "Yeti",
                "value": dbc.themes.YETI,
                "label_id": "theme-switch-label",
            },
        ],
        "value": dbc.themes.CYBORG,
        "persistence": True,
    },
    button_props={"style": {"height": "37px"}},
)
