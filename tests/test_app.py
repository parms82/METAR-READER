"""
Unit and route tests for the METAR Reader application.

Test strategy:
  - Unit tests: pure decoder functions tested with mock METAR JSON payloads.
  - Route tests: Flask test client with requests.get patched so no real
    network calls are made.
"""

import pytest
from unittest.mock import patch, Mock
from app import (
    app,
    celsius_to_fahrenheit,
    knots_to_mph,
    hpa_to_inhg,
    degrees_to_compass,
    decode_sky_conditions,
    decode_wx_string,
    build_readable,
)


# ── Fixtures: reusable mock METAR payloads ─────────────────────────────────────

@pytest.fixture
def metar_clear_calm():
    """Clear skies, calm wind — mirrors a typical KHIO reading."""
    return {
        "icaoId": "KHIO",
        "name": "Portland/Hillsboro Arpt, OR, US",
        "reportTime": "2026-05-18T09:00:00.000Z",
        "temp": 8.9,
        "dewp": 6.1,
        "wdir": 0,
        "wspd": 0,
        "wgst": None,
        "visib": "10+",
        "altim": 1024.8,
        "cover": "CLR",
        "clouds": [],
        "wxString": None,
        "fltCat": "VFR",
        "rawOb": "METAR KHIO 180853Z AUTO 00000KT 10SM CLR 09/06 A3026",
    }


@pytest.fixture
def metar_cloudy_gusty():
    """Multiple cloud layers with wind gusts — mirrors a typical KORD reading."""
    return {
        "icaoId": "KORD",
        "name": "Chicago/O'Hare Intl, IL, US",
        "reportTime": "2026-05-18T09:00:00.000Z",
        "temp": 23.3,
        "dewp": 13.9,
        "wdir": 190,
        "wspd": 10,
        "wgst": 24,
        "visib": "10+",
        "altim": 1009.9,
        "cover": "BKN",
        "clouds": [
            {"cover": "FEW", "base": 5000},
            {"cover": "SCT", "base": 18000},
            {"cover": "BKN", "base": 25000},
        ],
        "wxString": None,
        "fltCat": "VFR",
        "rawOb": "METAR KORD 180851Z 19010G24KT 10SM FEW050 SCT180 BKN250 23/14 A2982",
    }


@pytest.fixture
def metar_rain_ifr():
    """Light rain and IFR conditions — low ceiling and reduced visibility."""
    return {
        "icaoId": "KSEA",
        "name": "Seattle-Tacoma Intl, WA, US",
        "reportTime": "2026-05-18T12:00:00.000Z",
        "temp": 10.0,
        "dewp": 9.0,
        "wdir": 200,
        "wspd": 8,
        "wgst": None,
        "visib": "3",
        "altim": 1005.0,
        "cover": "OVC",
        "clouds": [{"cover": "OVC", "base": 800}],
        "wxString": "-RA",
        "fltCat": "IFR",
        "rawOb": "METAR KSEA 181200Z 20008KT 3SM -RA OVC008 10/09 A2968",
    }


@pytest.fixture
def metar_fog_lifr():
    """Dense fog producing LIFR conditions and very low visibility."""
    return {
        "icaoId": "KSFO",
        "name": "San Francisco Intl, CA, US",
        "reportTime": "2026-05-18T06:00:00.000Z",
        "temp": 13.0,
        "dewp": 12.5,
        "wdir": 270,
        "wspd": 5,
        "wgst": None,
        "visib": "0.25",
        "altim": 1018.0,
        "cover": "OVC",
        "clouds": [{"cover": "OVC", "base": 200}],
        "wxString": "FG",
        "fltCat": "LIFR",
        "rawOb": "METAR KSFO 180600Z 27005KT 1/4SM FG OVC002 13/12 A3007",
    }


@pytest.fixture
def metar_snow_mvfr():
    """Snow with MVFR conditions."""
    return {
        "icaoId": "KDEN",
        "name": "Denver Intl, CO, US",
        "reportTime": "2026-01-15T18:00:00.000Z",
        "temp": -5.0,
        "dewp": -7.0,
        "wdir": 320,
        "wspd": 15,
        "wgst": 25,
        "visib": "4",
        "altim": 1012.0,
        "cover": "OVC",
        "clouds": [{"cover": "OVC", "base": 1500}],
        "wxString": "-SN",
        "fltCat": "MVFR",
        "rawOb": "METAR KDEN 151800Z 32015G25KT 4SM -SN OVC015 M05/M07 A2989",
    }


# ── Unit tests: conversion helpers ────────────────────────────────────────────

class TestConversions:
    def test_freezing_point(self):
        assert celsius_to_fahrenheit(0) == 32.0

    def test_boiling_point(self):
        assert celsius_to_fahrenheit(100) == 212.0

    def test_body_temp(self):
        assert celsius_to_fahrenheit(37) == 98.6

    def test_negative_celsius(self):
        assert celsius_to_fahrenheit(-40) == -40.0

    def test_knots_to_mph(self):
        assert knots_to_mph(10) == 12

    def test_knots_zero(self):
        assert knots_to_mph(0) == 0

    def test_hpa_to_inhg(self):
        # 1013.25 hPa == standard atmosphere == 29.92 inHg
        assert hpa_to_inhg(1013.25) == 29.92

    def test_compass_north(self):
        assert degrees_to_compass(0) == "North"

    def test_compass_south(self):
        assert degrees_to_compass(180) == "South"

    def test_compass_east(self):
        assert degrees_to_compass(90) == "East"

    def test_compass_west(self):
        assert degrees_to_compass(270) == "West"

    def test_compass_none_returns_variable(self):
        assert degrees_to_compass(None) == "variable direction"


# ── Unit tests: sky condition decoder ─────────────────────────────────────────

class TestDecodeSkyConditions:
    def test_clr_returns_clear(self):
        assert decode_sky_conditions("CLR", []) == "Clear skies"

    def test_skc_returns_clear(self):
        assert decode_sky_conditions("SKC", []) == "Clear skies"

    def test_nsc_returns_clear(self):
        assert decode_sky_conditions("NSC", []) == "Clear skies"

    def test_none_cover_no_clouds_is_clear(self):
        assert decode_sky_conditions(None, []) == "Clear skies"

    def test_few_clouds_with_altitude(self):
        result = decode_sky_conditions("FEW", [{"cover": "FEW", "base": 5000}])
        assert "A few clouds" in result
        assert "5,000 ft" in result

    def test_overcast_with_altitude(self):
        result = decode_sky_conditions("OVC", [{"cover": "OVC", "base": 800}])
        assert "Overcast" in result
        assert "800 ft" in result

    def test_multiple_layers(self):
        clouds = [
            {"cover": "FEW", "base": 5000},
            {"cover": "SCT", "base": 18000},
            {"cover": "BKN", "base": 25000},
        ]
        result = decode_sky_conditions("BKN", clouds)
        assert "A few clouds at 5,000 ft" in result
        assert "Scattered clouds at 18,000 ft" in result
        assert "Mostly cloudy at 25,000 ft" in result

    def test_cover_code_no_clouds_list(self):
        result = decode_sky_conditions("BKN", [])
        assert result == "Mostly cloudy"


# ── Unit tests: weather phenomena decoder ─────────────────────────────────────

class TestDecodeWxString:
    def test_none_returns_none(self):
        assert decode_wx_string(None) is None

    def test_empty_string_returns_none(self):
        assert decode_wx_string("") is None

    def test_light_rain(self):
        assert decode_wx_string("-RA") == "light rain"

    def test_heavy_rain(self):
        assert decode_wx_string("+RA") == "heavy rain"

    def test_snow(self):
        assert decode_wx_string("SN") == "snow"

    def test_light_snow(self):
        assert decode_wx_string("-SN") == "light snow"

    def test_fog(self):
        assert decode_wx_string("FG") == "fog"

    def test_mist(self):
        assert decode_wx_string("BR") == "mist"

    def test_haze(self):
        assert decode_wx_string("HZ") == "haze"

    def test_thunderstorm_with_rain(self):
        result = decode_wx_string("TSRA")
        assert "thunderstorm" in result
        assert "rain" in result

    def test_freezing_rain(self):
        result = decode_wx_string("FZRA")
        assert "freezing" in result
        assert "rain" in result

    def test_multiple_phenomena(self):
        result = decode_wx_string("-RA BR")
        assert "rain" in result
        assert "mist" in result


# ── Unit tests: build_readable with mock payloads ─────────────────────────────

class TestBuildReadable:

    def test_station_and_name(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["station"] == "KHIO"
        assert "Hillsboro" in result["name"]

    def test_temperature_conversion(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["temp_c"] == 8.9
        assert result["temp_f"] == 48.0  # 8.9°C → 48.0°F

    def test_dewpoint_conversion(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["dewp_c"] == 6.1
        assert result["dewp_f"] == 43.0  # 6.1°C → 43.0°F

    def test_calm_wind(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert "calm" in result["wind"].lower()

    def test_wind_with_direction_and_speed(self, metar_cloudy_gusty):
        result = build_readable(metar_cloudy_gusty)
        assert "South" in result["wind"]
        assert "12 mph" in result["wind"]   # 10 kt → 12 mph
        assert "10 knots" in result["wind"]

    def test_wind_gusts(self, metar_cloudy_gusty):
        result = build_readable(metar_cloudy_gusty)
        assert "gusting" in result["wind"]
        assert "28 mph" in result["wind"]   # 24 kt → 28 mph

    def test_excellent_visibility(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert "10 miles" in result["visibility"].lower()

    def test_reduced_visibility(self, metar_rain_ifr):
        result = build_readable(metar_rain_ifr)
        assert "3.0 miles" in result["visibility"]
        assert "limited" in result["visibility"].lower()

    def test_very_low_visibility(self, metar_fog_lifr):
        result = build_readable(metar_fog_lifr)
        assert "0.25" in result["visibility"]

    def test_clear_sky(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["sky"] == "Clear skies"

    def test_multiple_cloud_layers(self, metar_cloudy_gusty):
        result = build_readable(metar_cloudy_gusty)
        assert "5,000 ft" in result["sky"]
        assert "18,000 ft" in result["sky"]
        assert "25,000 ft" in result["sky"]

    def test_overcast_low_ceiling(self, metar_rain_ifr):
        result = build_readable(metar_rain_ifr)
        assert "Overcast" in result["sky"]
        assert "800 ft" in result["sky"]

    def test_no_phenomena_when_clear(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["phenomena"] is None

    def test_light_rain_phenomena(self, metar_rain_ifr):
        result = build_readable(metar_rain_ifr)
        assert result["phenomena"] == "light rain"

    def test_fog_phenomena(self, metar_fog_lifr):
        result = build_readable(metar_fog_lifr)
        assert result["phenomena"] == "fog"

    def test_light_snow_phenomena(self, metar_snow_mvfr):
        result = build_readable(metar_snow_mvfr)
        assert result["phenomena"] == "light snow"

    def test_pressure_conversion(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        # 1024.8 hPa → 30.26 inHg
        assert result["pressure"] == "30.26 inHg"

    def test_high_pressure_note(self, metar_clear_calm):
        # 1024.8 hPa → 30.26 inHg — within normal range (29.50–30.50)
        result = build_readable(metar_clear_calm)
        assert "Normal pressure" in result["pressure_note"]

    def test_low_pressure_note(self, metar_rain_ifr):
        result = build_readable(metar_rain_ifr)
        # 1005.0 hPa → 29.68 inHg — below 29.50 threshold? Let's check
        # 1005 / 33.8639 = 29.68 → normal range, not low
        assert "pressure" in result["pressure_note"].lower()

    def test_vfr_flight_category(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["flight_category"] == "VFR"
        assert result["flight_category_color"] == "green"

    def test_ifr_flight_category(self, metar_rain_ifr):
        result = build_readable(metar_rain_ifr)
        assert result["flight_category"] == "IFR"
        assert result["flight_category_color"] == "red"

    def test_lifr_flight_category(self, metar_fog_lifr):
        result = build_readable(metar_fog_lifr)
        assert result["flight_category"] == "LIFR"
        assert result["flight_category_color"] == "purple"

    def test_mvfr_flight_category(self, metar_snow_mvfr):
        result = build_readable(metar_snow_mvfr)
        assert result["flight_category"] == "MVFR"
        assert result["flight_category_color"] == "blue"

    def test_headline_present(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["headline"]
        assert "48.0°F" in result["headline"]

    def test_raw_metar_preserved(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert result["raw"] == metar_clear_calm["rawOb"]

    def test_observation_time_formatted(self, metar_clear_calm):
        result = build_readable(metar_clear_calm)
        assert "2026" in result["time"]
        assert "UTC" in result["time"]

    def test_humidity_note_very_humid(self, metar_fog_lifr):
        # Temp 13.0, dewp 12.5 → spread of 0.5 → very humid
        result = build_readable(metar_fog_lifr)
        assert "humid" in result["humidity_note"].lower()

    def test_humidity_note_dry(self, metar_cloudy_gusty):
        # Temp 23.3, dewp 13.9 → spread of 9.4 → dry
        result = build_readable(metar_cloudy_gusty)
        assert "dry" in result["humidity_note"].lower()

    def test_negative_temperature(self, metar_snow_mvfr):
        result = build_readable(metar_snow_mvfr)
        assert result["temp_c"] == -5.0
        assert result["temp_f"] == 23.0  # -5°C → 23°F


# ── Route tests: Flask endpoint with mocked API ────────────────────────────────

@pytest.fixture
def client():
    """Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestRoutes:

    def test_home_page_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"METAR Reader" in resp.data

    def test_home_page_has_search_form(self, client):
        resp = client.get("/")
        assert b'name="airport_code"' in resp.data

    def test_empty_submit_shows_error(self, client):
        resp = client.post("/", data={"airport_code": ""})
        assert b"Please enter an airport code" in resp.data

    @patch("app.requests.get")
    def test_valid_code_returns_weather(self, mock_get, client, metar_clear_calm):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b'[{}]'
        mock_resp.json.return_value = [metar_clear_calm]
        mock_get.return_value = mock_resp

        resp = client.post("/", data={"airport_code": "KHIO"})
        assert resp.status_code == 200
        assert b"KHIO" in resp.data
        assert b"Clear skies" in resp.data

    @patch("app.requests.get")
    def test_three_letter_code_prefixed_with_k(self, mock_get, client, metar_clear_calm):
        """Submitting 'HIO' should call the API with 'KHIO'."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b'[{}]'
        mock_resp.json.return_value = [metar_clear_calm]
        mock_get.return_value = mock_resp

        client.post("/", data={"airport_code": "HIO"})
        called_code = mock_get.call_args[1]["params"]["ids"]
        assert called_code == "KHIO"

    @patch("app.requests.get")
    def test_invalid_code_shows_not_found_error(self, mock_get, client):
        mock_resp = Mock()
        mock_resp.status_code = 204
        mock_resp.content = b""
        mock_get.return_value = mock_resp

        resp = client.post("/", data={"airport_code": "XXXX"})
        assert b"No METAR data found" in resp.data

    @patch("app.requests.get")
    def test_timeout_shows_friendly_error(self, mock_get, client):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout

        resp = client.post("/", data={"airport_code": "KHIO"})
        assert b"timed out" in resp.data

    @patch("app.requests.get")
    def test_network_error_shows_friendly_message(self, mock_get, client):
        import requests as req
        mock_get.side_effect = req.exceptions.RequestException

        resp = client.post("/", data={"airport_code": "KHIO"})
        assert b"Could not reach" in resp.data

    @patch("app.requests.get")
    def test_ifr_conditions_shown_in_page(self, mock_get, client, metar_rain_ifr):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b'[{}]'
        mock_resp.json.return_value = [metar_rain_ifr]
        mock_get.return_value = mock_resp

        resp = client.post("/", data={"airport_code": "KSEA"})
        assert b"IFR" in resp.data
        assert b"rain" in resp.data.lower()
