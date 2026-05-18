from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

METAR_API_URL = "https://aviationweather.gov/api/data/metar"


def celsius_to_fahrenheit(c):
    return round(c * 9 / 5 + 32, 1)


def knots_to_mph(knots):
    return round(knots * 1.15078)


def hpa_to_inhg(hpa):
    return round(hpa / 33.8639, 2)


def degrees_to_compass(degrees):
    if degrees is None:
        return "variable direction"
    directions = [
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest",
    ]
    return directions[round(degrees / 22.5) % 16]


def decode_sky_conditions(cover, clouds):
    """
    cover  – highest-cover code string (e.g. 'CLR', 'BKN')
    clouds – list of {'cover': 'FEW', 'base': 5000} dicts
    """
    if cover in ("SKC", "CLR", "NSC", "NCD") or (cover is None and not clouds):
        return "Clear skies"

    cover_labels = {
        "FEW": "A few clouds",
        "SCT": "Scattered clouds",
        "BKN": "Mostly cloudy",
        "OVC": "Overcast",
        "VV":  "Sky obscured (very low visibility)",
    }

    if not clouds:
        return cover_labels.get(cover, cover)

    parts = []
    for layer in clouds:
        c = layer.get("cover", "")
        base = layer.get("base")
        label = cover_labels.get(c, c)
        if base:
            parts.append(f"{label} at {base:,} ft")
        else:
            parts.append(label)
    return ", ".join(parts)


def decode_wx_string(wx):
    if not wx:
        return None

    intensity_map  = {"-": "light ",   "+": "heavy ",  "VC": "nearby "}
    descriptor_map = {
        "MI": "shallow ",    "PR": "partial ",     "BC": "patches of ",
        "DR": "low drifting ","BL": "blowing ",     "SH": "shower of ",
        "TS": "thunderstorm with ", "FZ": "freezing ",
    }
    precip_map = {
        "DZ": "drizzle",  "RA": "rain",       "SN": "snow",
        "SG": "snow grains","IC": "ice crystals","PL": "ice pellets",
        "GR": "hail",     "GS": "small hail", "UP": "unknown precipitation",
    }
    obscure_map = {
        "BR": "mist",   "FG": "fog",     "FU": "smoke",
        "VA": "volcanic ash","DU": "dust","SA": "sand",
        "HZ": "haze",   "PY": "spray",
    }
    other_map = {
        "PO": "dust devils", "SQ": "squalls",
        "FC": "tornado/waterspout", "SS": "sandstorm", "DS": "dust storm",
    }

    all_phenomena = {**precip_map, **obscure_map, **other_map}
    decoded = []

    for token in wx.split():
        prefix = ""
        rest = token

        for sym, label in intensity_map.items():
            if rest.startswith(sym):
                prefix = label
                rest = rest[len(sym):]
                break

        for code, label in descriptor_map.items():
            if rest.startswith(code):
                prefix += label
                rest = rest[len(code):]
                break

        decoded.append(prefix + all_phenomena.get(rest, rest))

    return ", ".join(decoded)


FLIGHT_CATEGORIES = {
    "VFR":  ("Good flying conditions — clear and visible",             "green"),
    "MVFR": ("Marginal — reduced visibility or ceiling",               "blue"),
    "IFR":  ("Poor conditions — instruments required",                 "red"),
    "LIFR": ("Very poor conditions — extremely low visibility",        "purple"),
}


def build_readable(data):
    out = {
        "raw":     data.get("rawOb", ""),
        "station": data.get("icaoId", ""),
        "name":    data.get("name", ""),
    }

    # Time — ISO format: "2026-05-18T09:00:00.000Z"
    report_time = data.get("reportTime", "")
    if report_time:
        try:
            dt = datetime.strptime(report_time[:19], "%Y-%m-%dT%H:%M:%S")
            out["time"] = dt.strftime("%B %d, %Y — %H:%M UTC")
        except ValueError:
            out["time"] = report_time

    # Temperature & dewpoint
    temp_c = data.get("temp")
    dewp_c = data.get("dewp")
    if temp_c is not None:
        out["temp_f"] = celsius_to_fahrenheit(temp_c)
        out["temp_c"] = round(temp_c, 1)
    if dewp_c is not None:
        out["dewp_f"] = celsius_to_fahrenheit(dewp_c)
        out["dewp_c"] = round(dewp_c, 1)
        if temp_c is not None:
            spread = temp_c - dewp_c
            if spread <= 3:
                out["humidity_note"] = "Very humid — fog possible"
            elif spread <= 8:
                out["humidity_note"] = "Moderately humid"
            else:
                out["humidity_note"] = "Relatively dry air"

    # Wind
    wdir = data.get("wdir")
    wspd = data.get("wspd")
    wgst = data.get("wgst")

    if not wspd:
        out["wind"] = "Calm — no wind"
    else:
        compass = degrees_to_compass(wdir)
        mph = knots_to_mph(wspd)
        out["wind"] = f"From the {compass} at {mph} mph ({wspd} knots)"
        if wgst:
            out["wind"] += f", gusting to {knots_to_mph(wgst)} mph ({wgst} knots)"

    # Visibility
    visib = data.get("visib")
    if visib is not None:
        if str(visib) == "10+":
            out["visibility"] = "More than 10 miles — excellent visibility"
        else:
            try:
                v = float(visib)
                suffix = "mile" if v == 1 else "miles"
                note = " — reduced visibility" if v < 3 else (" — limited visibility" if v < 5 else "")
                out["visibility"] = f"{v} {suffix}{note}"
            except (ValueError, TypeError):
                out["visibility"] = str(visib)

    # Sky conditions — use `cover` + `clouds` array (base, not cloudBase)
    cover = data.get("cover")
    clouds = data.get("clouds", []) or []
    out["sky"] = decode_sky_conditions(cover, clouds)

    # Weather phenomena
    out["phenomena"] = decode_wx_string(data.get("wxString"))

    # Pressure — altim is in hPa; convert to inHg for display
    altim_hpa = data.get("altim")
    if altim_hpa:
        inhg = hpa_to_inhg(altim_hpa)
        out["pressure"] = f"{inhg} inHg"
        if inhg < 29.50:
            out["pressure_note"] = "Low pressure — stormy weather possible"
        elif inhg > 30.50:
            out["pressure_note"] = "High pressure — fair, stable weather"
        else:
            out["pressure_note"] = "Normal pressure"

    # Flight category — field is `fltCat` (capital C)
    fltcat = data.get("fltCat")
    if fltcat and fltcat in FLIGHT_CATEGORIES:
        desc, color = FLIGHT_CATEGORIES[fltcat]
        out["flight_category"]       = fltcat
        out["flight_category_desc"]  = desc
        out["flight_category_color"] = color

    out["headline"] = _make_headline(out)
    return out


def _make_headline(d):
    parts = []
    sky = d.get("sky", "")
    phenomena = d.get("phenomena")

    if phenomena:
        parts.append(f"Expect {phenomena}")
    elif "overcast" in sky.lower():
        parts.append("Overcast skies")
    elif "mostly cloudy" in sky.lower():
        parts.append("Mostly cloudy")
    elif "scattered" in sky.lower():
        parts.append("Partly cloudy")
    elif "few" in sky.lower():
        parts.append("Mostly clear with a few clouds")
    else:
        parts.append("Clear skies")

    temp_f = d.get("temp_f")
    if temp_f is not None:
        parts.append(f"{temp_f}°F")

    wind = d.get("wind", "")
    if "calm" in wind.lower():
        parts.append("calm winds")
    elif wind:
        # Trim to "From the South at 10 mph" style
        at_idx = wind.find(" at ")
        if at_idx != -1:
            end = wind.find(",", at_idx)
            short = wind[:end] if end != -1 else wind
            parts.append(short.lower())

    return " · ".join(parts)


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None
    airport_code = ""

    if request.method == "POST":
        raw_input = request.form.get("airport_code", "").strip().upper()
        airport_code = raw_input

        if not raw_input:
            error = "Please enter an airport code."
        else:
            code = raw_input
            if len(code) == 3 and code.isalpha():
                code = "K" + code

            try:
                resp = requests.get(
                    METAR_API_URL,
                    params={"ids": code, "format": "json"},
                    timeout=10,
                )
                resp.raise_for_status()

                # 204 No Content means valid request but no data for that station
                if resp.status_code == 204 or not resp.content.strip():
                    error = (
                        f'No METAR data found for "{raw_input}". '
                        "Check the airport code and try again — "
                        "US airports use 4-letter ICAO codes (e.g., KHIO, KLAX, KJFK)."
                    )
                    return render_template("index.html", weather=None, error=error, airport_code=airport_code)

                payload = resp.json()

                if payload and isinstance(payload, list) and len(payload) > 0:
                    weather = build_readable(payload[0])
                    airport_code = code
                else:
                    error = (
                        f'No METAR data found for "{raw_input}". '
                        "Check the airport code and try again — "
                        "US airports use 4-letter ICAO codes (e.g., KHIO, KLAX, KJFK)."
                    )

            except requests.exceptions.Timeout:
                error = "The weather service timed out. Please try again in a moment."
            except requests.exceptions.RequestException:
                error = "Could not reach the weather service. Please check your connection and try again."
            except (ValueError, KeyError):
                error = "Received unexpected data from the weather service. Please try again."

    return render_template("index.html", weather=weather, error=error, airport_code=airport_code)


if __name__ == "__main__":
    app.run(debug=True)
