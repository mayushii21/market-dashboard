from innov8.components.charts_52w import carousel_52_week
from innov8.components.dropdowns import dropdown_1, dropdown_2
from innov8.components.intra_sector import intra_sector_data, table_info
from innov8.components.main_carousel import carousel
from innov8.components.price_card import price_card
from innov8.components.price_chart import ema_switch, price_chart, sma_switch
from innov8.components.update import update_button, update_state


def test_carousel():
    carousel_data = carousel()
    # Check that the settings are correct
    assert carousel_data.autoplay is True
    assert carousel_data.speed == 500
    assert carousel_data.slides_to_show == 5
    # Ensure proper data types for span children, as well as color
    for child in carousel_data.children:
        color = (
            isinstance(child.children[0].children, str)  # True
            and isinstance(child.children[1].children, str)  # True
            and child.children[1].style["color"]
        )
        assert color in {"green", "red"}


def test_carousel_52_week():
    carousel_data = carousel_52_week()
    # Check that the settings are correct
    assert carousel_data.autoplay is True
    assert carousel_data.speed == 3000
    assert carousel_data.slides_to_show == 1
    # Verify that the carousel contains proper components
    assert carousel_data.children[0].id == "52-week-price-chart"
    assert carousel_data.children[1].id == "52-week-high-low-indicator"


def test_dropdowns():
    dd_1 = dropdown_1()
    dd_2 = dropdown_2()
    # Check settings
    assert dd_1.clearable is False and dd_2.clearable is False
    # Verify proper components
    assert dd_1.id == "sector-dropdown"
    assert dd_2.id == "symbol-dropdown"
    # Verify options data type
    assert {isinstance(option, str) for option in dd_1.options} == {True}


def test_update_button():
    update_group_data = update_button()
    # Check settings
    assert update_group_data.children[0].outline is True
    assert update_group_data.children[1].options == ["Ticker", "Sector", "All"]
    assert update_group_data.children[1].value == "Ticker"
    assert update_group_data.children[1].clearable is False
    # Verify proper components
    assert update_group_data.children[0].id == "update-button"
    assert update_group_data.children[1].id == "update-dropdown"


def test_stores():
    isd = intra_sector_data()
    us = update_state()
    # Check storage type
    assert isd.storage_type == us.storage_type == "session"
    # Verify proper components
    assert isd.id == "intra_sector_data"
    assert us.id == "update-state"


def test_table():
    table_data = table_info()
    # Check settings
    assert table_data.children[1].style_table["overflowY"] == "auto"
    assert (
        table_data.children[1].style_data["backgroundColor"]
        == table_data.children[1].style_header["backgroundColor"]
        == "rgba(0,0,0,0)"
    )
    # Verify proper component
    assert table_data.children[1].id == "correlation-table"


def test_price_card():
    price_card_data = price_card()
    # Verify proper components
    assert price_card_data.children[0].id == "ticker-symbol"
    assert price_card_data.children[1].id == "ticker-name"
    assert price_card_data.children[2].id == "ticker-price"
    assert price_card_data.children[3].id == "ticker-change"
    assert price_card_data.children[4].id == "exchange-name"
    assert price_card_data.children[5].id == "economic-sector"


def test_switches():
    ema_switch_data = ema_switch()
    sma_switch_data = sma_switch()
    # Check settings
    assert ema_switch_data.children[0].children.persistence is True
    assert sma_switch_data.children[0].children.persistence is True
    assert ema_switch_data.children[1].persistence is True
    assert sma_switch_data.children[1].persistence is True
    assert ema_switch_data.children[1].type == "number"
    assert sma_switch_data.children[1].type == "number"
    # Verify proper components
    assert ema_switch_data.children[0].children.id == "ema"
    assert ema_switch_data.children[1].id == "ema-period"
    assert sma_switch_data.children[0].children.id == "sma"
    assert sma_switch_data.children[1].id == "sma-period"


def test_price_chart():
    # Verify proper component
    assert price_chart().id == "price-chart"
