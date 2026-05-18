# METAR Reader

A simple web application that fetches live airport weather reports (METARs) and translates the cryptic aviation shorthand into plain, friendly English.

Type in an airport code and get a clear summary like:
> **Mostly cloudy · 73°F · winds from the South at 12 mph, gusting to 28 mph**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey)
![Data](https://img.shields.io/badge/Data-aviationweather.gov-green)

---

## What is a METAR?

A METAR (Meteorological Aerodrome Report) is a standardized weather observation issued by airports around the world. They look like this:

```
METAR KORD 180851Z 19010G24KT 10SM FEW050 SCT180 BKN250 23/14 A2982
```

This app decodes that into:
- Temperature in °F and °C
- Wind direction, speed, and gusts in mph
- Visibility with a plain-English qualifier
- Sky conditions with cloud layer altitudes
- Barometric pressure in inHg
- Flight category (VFR / MVFR / IFR / LIFR)
- A one-line weather headline

---

## Installation

### Requirements
- Python 3.10 or higher
- Internet connection (live data from [aviationweather.gov](https://aviationweather.gov))

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/parms82/METAR-READER.git
cd METAR-READER
```

**2. Create a virtual environment**
```bash
python3 -m venv .venv
```

**3. Activate the virtual environment**

On macOS / Linux:
```bash
source .venv/bin/activate
```

On Windows:
```bash
.venv\Scripts\activate
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Run the app**
```bash
python app.py
```

**6. Open in your browser**
```
http://127.0.0.1:5000
```

---

## Usage

1. Enter a **4-letter ICAO airport code** in the search box (e.g. `KHIO`, `KLAX`, `KJFK`)
2. 3-letter US codes also work — the app adds the `K` prefix automatically (e.g. `LAX` → `KLAX`)
3. Press **Get Weather** to see the decoded report

### Example airport codes

| Code | Airport |
|------|---------|
| `KHIO` | Portland/Hillsboro, OR |
| `KLAX` | Los Angeles International, CA |
| `KJFK` | John F. Kennedy International, NY |
| `KORD` | Chicago O'Hare International, IL |
| `KSEA` | Seattle-Tacoma International, WA |
| `EGLL` | London Heathrow, UK |
| `RJTT` | Tokyo Haneda, Japan |

---

## Project Structure

```
METAR-READER/
├── app.py               # Flask application and METAR decoder
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Front-end UI
└── README.md
```

---

## Data Source

Live METAR data is provided by the **Aviation Weather Center** (NOAA):
[https://aviationweather.gov/api/data/metar](https://aviationweather.gov/api/data/metar)

This is a free, public API — no API key required.

---

## License

MIT License — free to use, modify, and distribute.
