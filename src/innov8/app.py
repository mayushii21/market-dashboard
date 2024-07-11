import dash_bootstrap_components as dbc
import diskcache
from dash import Dash, DiskcacheManager

# Initiate dash app with default theme (visible for a split second before theme from ThemeChangerAIO takes over)
default_theme = dbc.themes.CYBORG
# css for styling dcc and html components with dbc themes
dbc_css = (
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.8/dbc.min.css"
)

cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

app = Dash(
    __name__,
    external_stylesheets=[default_theme, dbc_css],
    title="innov8finance",
    background_callback_manager=background_callback_manager,
    suppress_callback_exceptions=True,
)
