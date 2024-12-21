from unittest.mock import patch

import pytest

from innov8.components.charts_52w import update_52_week_charts
from innov8.components.dropdowns import update_symbols_dropdown
from innov8.components.intra_sector import (
    calculate_table_data,
    corrs,
    update_intra_sector_table,
)
from innov8.components.main_carousel import update_main_carousel
from innov8.components.price_card import update_symbol_data
from innov8.components.price_chart import (
    update_price_chart,
)
from innov8.components.update import update_button_style, update_ticker_data


def test_update_symbols_dropdown_tech_sector():
    # Test the update_symbols_dropdown function
    options, selected_value = update_symbols_dropdown("Technology")
    assert {"AAPL", "ACN", "ADBE", "ADI", "ADSK"}.issubset(options)
    assert selected_value == "AAPL"


@pytest.mark.parametrize(
    "inputs, output",
    [
        (
            ("Ticker", "AAPL", None, ["AAPL"]),
            (
                "Up to date",
                "success",
                True,
            ),
        ),
        (
            ("Ticker", None, "Technology", ["Technology"]),
            (
                "Up to date",
                "success",
                True,
            ),
        ),
        (
            ("Sector", None, "Technology", ["Technology"]),
            (
                "Up to date",
                "success",
                True,
            ),
        ),
        (
            ("All", None, None, ["All"]),
            (
                "Up to date",
                "success",
                True,
            ),
        ),
        (("Ticker", "AAPL", "Technology", ["not empty"]), (("Update", "info", False))),
    ],
)
def test_update_button_style(inputs, output):
    # Verify proper output
    assert update_button_style(*inputs) == output


def test_update_ticker_data():
    # Test proper return format
    assert update_ticker_data(True, "Ticker", None, None, None, {}) == {None: True}
    # # Use pytest.raises to check if PreventUpdate is raised
    # with pytest.raises(PreventUpdate):
    #     update_ticker_data(None, None, None, None, None, {})


def test_update_main_carousel():
    carousel_data = update_main_carousel(None)
    assert len(carousel_data) == 10
    # Verify proper color assignment
    for item in carousel_data:
        assert item.children and isinstance(item.children[0].children, str)
        assert (
            item.children[1].style["color"] == "green"
            if item.children[1].children[0] == "+"
            else item.children[1].style["color"] == "red"
        )


def test_update_symbol_data():
    output = update_symbol_data("AAPL", None)
    # Verify expected output
    assert output[0] == "AAPL"
    assert output[1] == "Apple Inc."
    assert output[5] == "Exchange: NMS"
    assert output[6] == "Sector: Technology"


# Fixture with calculated correlation table data
@pytest.fixture(scope="module")
def calculated_table_data() -> None:
    return calculate_table_data("Technology")


def test_calculate_table_data(calculated_table_data: None):
    df = corrs["Technology"]

    # Check that the correlation matrix is symmetric:
    # correlation(sym1, sym2) should equal correlation(sym2, sym1)
    for sym1 in df.columns:
        for sym2 in df.index:
            assert df.loc[sym1, sym2] == pytest.approx(
                df.loc[sym2, sym1]
            ), f"Matrix is not symmetric: {sym1}/{sym2} != {sym2}/{sym1}"

    # Check that all expected symbols are present
    symbols_to_check = {"AAPL", "AMD", "EPAM", "IBM", "MSFT", "NVDA"}
    missing_in_symbols = symbols_to_check - set(df.index)
    assert not missing_in_symbols, f"Missing symbols in rows: {missing_in_symbols}"


def test_update_intra_sector_table():
    # dash.callback_context.triggered_prop_ids is only available from a callback!
    with patch(
        "innov8.components.intra_sector.callback_context"
    ) as mock_callback_context:
        mock_callback_context.triggered_prop_ids = {
            "symbol-dropdown.value": "symbol-dropdown"
        }

        output = update_intra_sector_table("Technology", "AAPL", None)
        assert list(output[0].keys()) == ["symbol", "price", "90-day corr"]


# Define the mocked behavior for template_from_url
def mock_template_from_url(theme):
    return "plotly"


def mock_template_hex_color(url):
    # Return a template with a valid hex color for gridcolor
    return {"layout": {"scene": {"xaxis": {"gridcolor": "#123456"}}}}  # Valid hex color


def test_update_52_week_charts():
    # Use unittest.mock.patch to replace the template_from_url function with the mock
    with patch(
        "innov8.components.charts_52w.template_from_url",
        side_effect=mock_template_from_url,
    ):
        output = update_52_week_charts("AAPL", None, None)
        # Verify that two figures are successfully plotted
        assert {"data", "layout"}.issubset(set(dir(output[0])))
        assert {"data", "layout"}.issubset(set(dir(output[1])))


# Fixture with price chart figure
@pytest.fixture(scope="module")
def price_chart():
    # Use unittest.mock.patch to replace the template_from_url function with the mock
    with (
        patch(
            "innov8.components.price_chart.template_from_url",
            side_effect=mock_template_from_url,
        ),
        patch(
            "plotly.io.templates",
            new={
                "plotly": {
                    "layout": {
                        "scene": {"xaxis": {"gridcolor": "#123456"}},
                        "font": {"color": "#123456"},
                    }
                }
            },
        ),
    ):
        return update_price_chart("AAPL", True, True, 9, 50, None, None)
