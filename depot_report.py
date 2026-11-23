import io
import os
import sqlite3
import time
import zipfile
from datetime import date, datetime
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, "depot_data.db")

# 15 minutes inactivity timeout (15 * 60 = 900 seconds)
SESSION_TIMEOUT_SECONDS = 15 * 60

# Standard A4 at 300 DPI (210mm x 297mm)
A4_WIDTH = 2480
A4_HEIGHT = 3508

DEPOTS = [
    "LNG",
    "CAT",
    "BPG",
    "DNG",
    "PALDA",
    "MHOW",
    "Depalpur",
    "Gandhi Nagar",
]

PRODUCTS = [
    "PPC",
    "PLUS",
    "Xtreme",
]

USERS = {
    "admin": ("admin123", None),
    "lng": ("pass101", "LNG"),
    "cat": ("pass102", "CAT"),
    "bpg": ("pass103", "BPG"),
    "dng": ("pass104", "DNG"),
    "palda": ("pass105", "PALDA"),
    "mhow": ("pass106", "MHOW"),
    "depalpur": ("pass107", "Depalpur"),
    "gandhinagar": ("pass108", "Gandhi Nagar"),
}


def get_fonts(title_size=54, section_size=38, body_size=32, small_size=28):
    bold_candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    bold_path = next((p for p in bold_candidates if os.path.exists(p)), None)
    regular_path = next((p for p in regular_candidates if os.path.exists(p)), None)

    if bold_path and regular_path:
        return (
            ImageFont.truetype(bold_path, title_size),
            ImageFont.truetype(bold_path, section_size),
            ImageFont.truetype(regular_path, body_size),
            ImageFont.truetype(regular_path, small_size),
        )

    fallback = ImageFont.load_default()
    return fallback, fallback, fallback, fallback


def format_display_date(date_str):
    try:
        dt_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        return dt_obj.strftime("%d-%b-%y")
    except Exception:
        return str(date_str)


def inject_mvs_wonder_theme_css():
    st.markdown(
        """
        <style>
        /* Clean White & Mint Surface with #000000 Black Font and MVS & Wonder Accents */
        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stToolbar"],
        [data-testid="stBottomBlockContainer"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        .stApp p, .stApp span, .stApp label, .stApp div, .stApp li,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
            color: #000000 !important;
        }

        .block-container {
            padding-top: 1.0rem;
            padding-bottom: 2.2rem;
            max-width: 100%;
            background-color: #FFFFFF !important;
        }

        /* Top Brand Strip (Mangilal Vijayvargiya & Sons left, WONDER CEMENT right) */
        .brand-top-strip {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 18px;
            background-color: #FFFFFF !important;
            border-bottom: 1px solid #E2E8F0;
            margin-bottom: 10px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .mvs-brand-mark {
            color: #9A7B3E !important;
            font-size: 20px;
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: 0.4px;
        }

        .mvs-brand-sub {
            color: #475569 !important;
            font-size: 10px;
            letter-spacing: 1.4px;
            font-weight: 700;
        }

        .wonder-mark {
            color: #DC2626 !important;
            font-size: 16px;
            font-weight: 900;
            letter-spacing: 0.6px;
            text-align: right;
            line-height: 1.1;
        }

        .wonder-tagline {
            color: #DC2626 !important;
            font-size: 8px;
            letter-spacing: 1.2px;
            font-weight: 700;
            text-align: right;
        }

        /* MVS & Wonder Hero Title */
        .mvs-hero {
            text-align: center;
            margin-top: 6px;
            margin-bottom: 12px;
        }

        .mvs-title {
            font-size: 38px;
            font-weight: 800;
            color: #000000 !important;
            letter-spacing: -0.4px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .mvs-subtitle {
            color: #334155 !important;
            font-size: 12.5px;
            margin-top: 4px;
            font-weight: 600;
        }

        .get-started-heading {
            text-align: center;
            font-size: 16px;
            font-weight: 700;
            color: #000000 !important;
            margin: 10px 0 14px 0;
        }

        /* Internal Top Header Bar */
        .internal-topbar {
            background-color: #ECFDF5 !important;
            border: 1.5px solid #0284C7;
            padding: 12px 18px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
