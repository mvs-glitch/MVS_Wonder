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

        .mvs-badge {
            background-color: #E0F2FE !important;
            color: #000000 !important;
            font-size: 26px;
            font-weight: 800;
            padding: 2px 12px;
            border-radius: 6px;
            border: 1.5px solid #0284C7;
            line-height: 1.15;
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
            margin-bottom: 14px;
        }

        .internal-topbar-title {
            color: #000000 !important;
            font-size: 20px;
            font-weight: 800;
        }

        .internal-role-pill {
            background-color: #E0F2FE !important;
            color: #000000 !important;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 999px;
            border: 1px solid #0284C7;
        }

        .section-card-title {
            background-color: #ECFDF5 !important;
            color: #000000 !important;
            padding: 8px 14px;
            border-left: 5px solid #0284C7;
            border-top: 1px solid #A7F3D0;
            border-right: 1px solid #A7F3D0;
            border-bottom: 1px solid #A7F3D0;
            border-radius: 6px;
            font-weight: 800;
            margin: 10px 0 10px 0;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #ECFDF5 !important;
            padding: 6px;
            border-radius: 10px;
            border: 1px solid #0284C7;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 700;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
        }

        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span {
            color: #FFFFFF !important;
        }

        /* Soft ice-blue / white inputs with pure black text */
        [data-testid="stTextInput"] div,
        [data-testid="stNumberInput"] div,
        [data-testid="stDateInput"] div,
        [data-testid="stSelectbox"] div,
        [data-testid="stFileUploader"] section,
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        [data-testid="stForm"],
        div[data-baseweb="input"],
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="popover"],
        ul[role="listbox"],
        li[role="option"] {
            background-color: #EBF1FA !important;
            color: #000000 !important;
        }

        input, textarea, select {
            background-color: #EBF1FA !important;
            color: #000000 !important;
            caret-color: #000000 !important;
            border-color: #CBD5E1 !important;
        }

        input::placeholder, textarea::placeholder {
            color: #334155 !important;
            opacity: 1 !important;
        }

        [data-testid="stNumberInput"] button {
            background-color: #E0F2FE !important;
            color: #000000 !important;
            border-color: #0284C7 !important;
        }

        [data-testid="stNumberInput"] button * {
            color: #000000 !important;
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border-radius: 10px;
            border: 1.5px solid #CBD5E1 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            border: 1px solid #E2E8F0;
            padding: 6px 8px;
            display: flex;
            align-items: center;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        /* Unified button style matching LOGOUT & Delete: #0284C7 background with #FFFFFF text */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button,
        button[kind="primary"],
        button[kind="secondary"],
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-secondary"] {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
            border: 1.5px solid #0369A1 !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
        }

        .stButton > button *,
        .stDownloadButton > button *,
        .stButton > button p,
        .stButton > button span,
        .stDownloadButton > button p,
        .stDownloadButton > button span,
        [data-testid="stFormSubmitButton"] > button *,
        [data-testid="stFormSubmitButton"] > button p,
        [data-testid="stFormSubmitButton"] > button span {
            color: #FFFFFF !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            background-color: #0369A1 !important;
            border-color: #075985 !important;
            color: #FFFFFF !important;
        }

        .mvs-footer {
            text-align: center;
            color: #000000 !important;
            font-size: 12px;
            margin-top: 24px;
            padding-top: 10px;
            border-top: 1px solid #E2E8F0;
        }

        @media (max-width: 768px) {
            .mvs-brand-mark {
                font-size: 16px;
            }
            .mvs-title {
                font-size: 28px;
            }
            .mvs-badge {
                font-size: 20px;
            }
            .internal-topbar-title {
                font-size: 17px;
            }
            .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
                min-height: 42px;
                font-size: 14px;
            }
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header():
    st.markdown(
        """
        <div class="brand-top-strip">
            <div>
                <div class="mvs-brand-mark">Mangilal Vijayvargiya &amp; Sons</div>
                <div class="mvs-brand-sub">AUTHORIZED DISTRIBUTION PARTNER</div>
            </div>
            <div>
                <div class="wonder-mark">WONDER<br>CEMENT</div>
                <div class="wonder-tagline">FARQ NAZAR AAYEGA</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def check_and_refresh_session():
    now = time.time()
    if st.session_state.get("user") is not None:
        last_active = st.session_state.get("last_active_ts", now)
        if (now - last_active) >= SESSION_TIMEOUT_SECONDS:
            st.session_state.user = None
            st.session_state.last_active_ts = None
            st.session_state.session_expired_msg = True
            st.rerun()
        else:
            st.session_state.last_active_ts = now


@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS report_meta (
            depot TEXT NOT NULL,
            report_date TEXT NOT NULL,
            ppc_op INTEGER DEFAULT 0,
            plus_op INTEGER DEFAULT 0,
            xtreme_op INTEGER DEFAULT 0,
            op_set INTEGER DEFAULT 0,
            PRIMARY KEY (depot, report_date)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_party_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot TEXT NOT NULL,
            report_date TEXT NOT NULL,
            party TEXT NOT NULL,
            bag INTEGER NOT NULL,
            brand TEXT NOT NULL,
            truck TEXT DEFAULT '',
            created_by TEXT DEFAULT 'admin',
            status TEXT DEFAULT 'PENDING'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot TEXT NOT NULL,
            report_date TEXT NOT NULL,
            party TEXT NOT NULL,
            bag INTEGER NOT NULL,
            brand TEXT NOT NULL,
            truck TEXT DEFAULT '',
            approved_by TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inward_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot TEXT NOT NULL,
            report_date TEXT NOT NULL,
            truck TEXT NOT NULL,
            bag INTEGER NOT NULL,
            brand TEXT NOT NULL,
            roadline TEXT DEFAULT ''
        )
        """
    )

    cur.execute("PRAGMA table_info(dispatch_entries)")
    d_cols = [row[1] for row in cur.fetchall()]
    if "approved_by" not in d_cols:
        cur.execute("ALTER TABLE dispatch_entries ADD COLUMN approved_by TEXT DEFAULT ''")

    cur.execute("PRAGMA table_info(report_meta)")
    m_cols = [row[1] for row in cur.fetchall()]
    if "op_set" not in m_cols:
        cur.execute("ALTER TABLE report_meta ADD COLUMN op_set INTEGER DEFAULT 0")

    conn.commit()
    return conn


def _brand_in_out_for_date(conn, depot, target_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT brand, COALESCE(SUM(bag), 0)
        FROM inward_entries
        WHERE depot = ? AND report_date = ?
        GROUP BY brand
        """,
        (depot, target_date),
    )
    in_map = {row[0]: int(row[1] or 0) for row in cur.fetchall()}

    cur.execute(
        """
        SELECT brand, COALESCE(SUM(bag), 0)
        FROM dispatch_entries
        WHERE depot = ? AND report_date = ?
        GROUP BY brand
        """,
        (depot, target_date),
    )
    out_map = {row[0]: int(row[1] or 0) for row in cur.fetchall()}
    return in_map, out_map


def _closing_stock_for_date(conn, depot, target_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ppc_op, plus_op, xtreme_op, op_set
        FROM report_meta
        WHERE depot = ? AND report_date = ?
        """,
        (depot, target_date),
    )
    meta = cur.fetchone()
    p_op = int(meta[0] or 0) if meta else 0
    pl_op = int(meta[1] or 0) if meta else 0
    x_op = int(meta[2] or 0) if meta else 0

    in_map, out_map = _brand_in_out_for_date(conn, depot, target_date)
    p_close = p_op + in_map.get("PPC", 0) - out_map.get("PPC", 0)
    pl_close = pl_op + in_map.get("PLUS", 0) - out_map.get("PLUS", 0)
    x_close = x_op + in_map.get("Xtreme", 0) - out_map.get("Xtreme", 0)
    return p_close, pl_close, x_close


def get_previous_closing_stock(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT report_date
        FROM report_meta
        WHERE depot = ? AND report_date < ?
        ORDER BY report_date DESC
        LIMIT 1
        """,
        (depot, report_date),
    )
    prev_meta = cur.fetchone()
    prev_meta_date = prev_meta[0] if prev_meta else None

    cur.execute(
        """
        SELECT MAX(dt) FROM (
            SELECT report_date AS dt FROM dispatch_entries WHERE depot = ? AND report_date < ?
            UNION
            SELECT report_date AS dt FROM inward_entries WHERE depot = ? AND report_date < ?
        )
        """,
        (depot, report_date, depot, report_date),
    )
    prev_tx = cur.fetchone()
    prev_tx_date = prev_tx[0] if prev_tx and prev_tx[0] else None

    candidates = [d for d in [prev_meta_date, prev_tx_date] if d]
    if not candidates:
        return 0, 0, 0

    latest_prev_date = max(candidates)
    return _closing_stock_for_date(conn, depot, latest_prev_date)


def load_meta(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ppc_op, plus_op, xtreme_op, op_set
        FROM report_meta
        WHERE depot = ? AND report_date = ?
        """,
        (depot, report_date),
    )
    row = cur.fetchone()

    if row:
        op_set = int(row[3] or 0)
        if op_set == 1:
            return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)

        prev_p, prev_pl, prev_x = get_previous_closing_stock(conn, depot, report_date)
        cur.execute(
            """
            UPDATE report_meta
            SET ppc_op = ?, plus_op = ?, xtreme_op = ?, op_set = 1
            WHERE depot = ? AND report_date = ?
            """,
            (prev_p, prev_pl, prev_x, depot, report_date),
        )
        conn.commit()
        return prev_p, prev_pl, prev_x

    prev_p, prev_pl, prev_x = get_previous_closing_stock(conn, depot, report_date)
    cur.execute(
        """
        INSERT INTO report_meta
        (depot, report_date, ppc_op, plus_op, xtreme_op, op_set)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (depot, report_date, prev_p, prev_pl, prev_x),
    )
    conn.commit()
    return prev_p, prev_pl, prev_x


def save_meta(conn, depot, report_date, p_op, pl_op, x_op, is_admin):
    load_meta(conn, depot, report_date)
    if not is_admin:
        return
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE report_meta
        SET ppc_op = ?, plus_op = ?, xtreme_op = ?, op_set = 1
        WHERE depot = ? AND report_date = ?
        """,
        (p_op, pl_op, x_op, depot, report_date),
    )
    conn.commit()


def submit_party_for_approval(conn, depot, report_date, party, bag, brand, truck, user_id):
    load_meta(conn, depot, report_date)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pending_party_entries
        (depot, report_date, party, bag, brand, truck, created_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """,
        (depot, report_date, party.strip(), int(bag), brand, truck.strip(), user_id),
    )
    conn.commit()


def approve_pending_entry(conn, pending_id, depot, report_date, approver_id):
    load_meta(conn, depot, report_date)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT depot, report_date, party, bag, brand, truck
            FROM pending_party_entries
            WHERE id = ? AND depot = ? AND report_date = ? AND status = 'PENDING'
            """,
            (int(pending_id), depot, report_date),
        )
        row = cur.fetchone()
        if not row:
            return False

        p_depot, p_date, party, bag, brand, truck = row
        cur.execute(
            """
            INSERT INTO dispatch_entries
            (depot, report_date, party, bag, brand, truck, approved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (p_depot, p_date, party, int(bag), brand, truck, approver_id),
        )
        cur.execute(
            """
            UPDATE pending_party_entries
            SET status = 'APPROVED'
            WHERE id = ?
            """,
            (int(pending_id),),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def delete_pending_by_id(conn, pending_id, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM pending_party_entries WHERE id = ? AND depot = ? AND report_date = ?",
        (int(pending_id), depot, report_date),
    )
    conn.commit()


def delete_dispatch_by_id(conn, entry_id, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM dispatch_entries WHERE id = ? AND depot = ? AND report_date = ?",
        (int(entry_id), depot, report_date),
    )
    conn.commit()


def delete_inward_by_id(conn, entry_id, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM inward_entries WHERE id = ? AND depot = ? AND report_date = ?",
        (int(entry_id), depot, report_date),
    )
    conn.commit()


def import_excel_file(conn, uploaded_file, depot, report_date, is_admin, user_id):
    load_meta(conn, depot, report_date)
    cur = conn.cursor()
    imported_d = 0
    imported_i = 0

    xl = pd.ExcelFile(uploaded_file)
    sheet_names = [s.lower() for s in xl.sheet_names]

    d_sheet = next(
        (xl.sheet_names[idx] for idx, name in enumerate(sheet_names) if "dispatch" in name or "out" in name),
        None,
    )
    if d_sheet:
        df_d = xl.parse(d_sheet)
        df_d.columns = [str(c).strip().lower() for c in df_d.columns]
        for _, row in df_d.iterrows():
            party = str(row.get("party", "")).strip()
            if not party or party.lower() == "nan":
                continue
            try:
                bag = int(float(row.get("bag", 0) or 0))
            except Exception:
                bag = 0
            if bag <= 0:
                continue
            brand = str(row.get("brand", "PPC")).strip()
            if brand not in PRODUCTS:
                brand = "PPC"
            truck = str(row.get("truck", "")).strip()
            if truck.lower() == "nan":
                truck = ""

            if is_admin:
                cur.execute(
                    """
                    INSERT INTO pending_party_entries
                    (depot, report_date, party, bag, brand, truck, created_by, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                    """,
                    (depot, report_date, party, bag, brand, truck, user_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO dispatch_entries
                    (depot, report_date, party, bag, brand, truck, approved_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (depot, report_date, party, bag, brand, truck, user_id),
                )
            imported_d += 1

    i_sheet = next(
        (xl.sheet_names[idx] for idx, name in enumerate(sheet_names) if "inward" in name or ("in" in name and "summary" not in name)),
        None,
    )
    if i_sheet:
        df_i = xl.parse(i_sheet)
        df_i.columns = [str(c).strip().lower() for c in df_i.columns]
        for _, row in df_i.iterrows():
            truck = str(row.get("truck", "")).strip()
            if not truck or truck.lower() == "nan":
                continue
            try:
                bag = int(float(row.get("bag", 0) or 0))
            except Exception:
                bag = 0
            if bag <= 0:
                continue
            brand = str(row.get("brand", "PPC")).strip()
            if brand not in PRODUCTS:
                brand = "PPC"
            roadline = str(row.get("roadline", row.get("from", ""))).strip()
            if roadline.lower() == "nan":
                roadline = ""
            cur.execute(
                """
                INSERT INTO inward_entries (depot, report_date, truck, bag, brand, roadline)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (depot, report_date, truck, bag, brand, roadline),
            )
            imported_i += 1

    conn.commit()
    return imported_d, imported_i


def compute_summary_rows(conn, depot, report_date, p_op, pl_op, x_op):
    in_map, out_map = _brand_in_out_for_date(conn, depot, report_date)

    rows = []
    tot_op = tot_in = tot_out = tot_bal = 0

    for label, key, op_val in [
        ("Wonder PPC", "PPC", p_op),
        ("Wonder PLUS", "PLUS", pl_op),
        ("Wonder Xtreme", "Xtreme", x_op),
    ]:
        in_val = in_map.get(key, 0)
        out_val = out_map.get(key, 0)
        bal_val = op_val + in_val - out_val

        tot_op += op_val
        tot_in += in_val
        tot_out += out_val
        tot_bal += bal_val

        rows.append(
            {
                "Brand": label,
                "OP-ST": op_val,
                "In": in_val,
                "Out": out_val,
                "Total": bal_val,
            }
        )

    rows.append(
        {
            "Brand": "Grand Total",
            "OP-ST": tot_op,
            "In": tot_in,
            "Out": tot_out,
            "Total": tot_bal,
        }
    )

    return pd.DataFrame(rows)


def _draw_centered_text(draw, box, text, font, fill="#000000"):
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), str(text), font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.text((tx, ty), str(text), font=font, fill=fill)


def _draw_row(draw, x_left, y, col_widths, row_h, values, font, fill="#FFFFFF"):
    cur_x = x_left
    for idx, w in enumerate(col_widths):
        box = (cur_x, y, cur_x + w, y + row_h)
        draw.rectangle(box, outline="#0284C7", width=3, fill=fill)
        _draw_centered_text(draw, box, values[idx], font, fill="#000000")
        cur_x += w


def _new_a4_page(depot, disp_date):
    f_title, f_sec, _, _ = get_fonts()
    img = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    margin_x = 85
    top_y = 85
    table_w = A4_WIDTH - (2 * margin_x)

    depot_h = 100
    draw.rectangle(
        (margin_x, top_y, margin_x + table_w, top_y + depot_h),
        outline="#0284C7",
        width=4,
        fill="#ECFDF5",
    )
    _draw_centered_text(
        draw,
        (margin_x, top_y, margin_x + table_w, top_y + depot_h),
        f"DEPOT : {depot}",
        f_title,
        fill="#000000",
    )

    meta_y = top_y + depot_h
    meta_h = 88

    draw.rectangle(
        (margin_x, meta_y, margin_x + table_w, meta_y + meta_h),
        outline="#0284C7",
        width=4,
        fill="#FFFFFF",
    )
    _draw_centered_text(
        draw,
        (margin_x, meta_y, margin_x + table_w, meta_y + meta_h),
        f"Date : {disp_date}",
        f_sec,
    )

    return img, draw, margin_x, table_w, meta_y + meta_h


def _stamp_page_numbers(pages):
    _, _, _, f_small = get_fonts()
    total_p = len(pages)
    for idx, img in enumerate(pages, start=1):
        draw = ImageDraw.Draw(img)
        footer_box = (85, A4_HEIGHT - 110, A4_WIDTH - 85, A4_HEIGHT - 45)
        _draw_centered_text(
            draw,
            footer_box,
            f"Page {idx} of {total_p}",
            f_small,
            fill="#000000",
        )


def build_a4_pages(depot, report_date, d_df, i_df, summary_df):
    _, f_sec, f_body, _ = get_fonts()
    disp_date = format_display_date(report_date)
    bottom_limit = A4_HEIGHT - 140

    pages = []
    img, draw, x_left, table_w, y = _new_a4_page(depot, disp_date)

    section_h = 78
    header_h = 72
    row_h = 70
    gap_h = 48

    col4 = [
        int(table_w * 0.34),
        int(table_w * 0.18),
        int(table_w * 0.18),
        table_w - int(table_w * 0.34) - int(table_w * 0.18) - int(table_w * 0.18),
    ]

    col5 = [
        int(table_w * 0.32),
        int(table_w * 0.17),
        int(table_w * 0.17),
        int(table_w * 0.17),
        table_w - int(table_w * 0.32) - (3 * int(table_w * 0.17)),
    ]

    def ensure_space(needed_h):
        nonlocal img, draw, y
        if y + needed_h > bottom_limit:
            pages.append(img)
            img, draw, x_left, table_w, y = _new_a4_page(depot, disp_date)

    # ---------------- DISPATCH (OUT) ----------------
    ensure_space(gap_h + section_h + header_h + row_h)
    y += gap_h
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#0284C7", width=3, fill="#ECFDF5")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "DISPATCH (OUT)", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col4, header_h, ["Party", "Bag", "Brand", "Truck"], f_sec, fill="#FFFFFF")
    y += header_h

    if d_df.empty:
        _draw_row(draw, x_left, y, col4, row_h, ["-", "0", "-", "-"], f_body)
        y += row_h
    else:
        for _, r in d_df.iterrows():
            ensure_space(row_h)
            _draw_row(
                draw,
                x_left,
                y,
                col4,
                row_h,
                [r["Party"], r["Bag"], r["Brand"], r["Truck"]],
                f_body,
            )
            y += row_h

    # ---------------- INWARD TRUCKS (IN) ----------------
    ensure_space(gap_h + section_h + header_h + row_h)
    y += gap_h
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#0284C7", width=3, fill="#E0F2FE")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "INWARD TRUCKS (IN)", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col4, header_h, ["Truck", "Bag", "Brand", "RoadLine"], f_sec, fill="#FFFFFF")
    y += header_h

    if i_df.empty:
        _draw_row(draw, x_left, y, col4, row_h, ["-", "0", "-", "-"], f_body)
        y += row_h
    else:
        for _, r in i_df.iterrows():
            ensure_space(row_h)
            _draw_row(
                draw,
                x_left,
                y,
                col4,
                row_h,
                [r["Truck"], r["Bag"], r["Brand"], r["RoadLine"]],
                f_body,
            )
            y += row_h

    # ---------------- BRAND STOCK SUMMARY ----------------
    needed_summary = gap_h + section_h + header_h + (len(summary_df) * row_h)
    ensure_space(needed_summary)
    y += gap_h
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#0284C7", width=3, fill="#ECFDF5")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "BRAND STOCK SUMMARY", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col5, header_h, ["Brand", "OP-ST", "In", "Out", "Total"], f_sec, fill="#FFFFFF")
    y += header_h

    for _, r in summary_df.iterrows():
        row_fill = "#E0F2FE" if str(r["Brand"]) == "Grand Total" else "#FFFFFF"
        _draw_row(
            draw,
            x_left,
            y,
            col5,
            row_h,
            [r["Brand"], r["OP-ST"], r["In"], r["Out"], r["Total"]],
            f_body,
            fill=row_fill,
        )
        y += row_h

    pages.append(img)
    _stamp_page_numbers(pages)
    return pages


def pages_to_jpg_bytes(page_img):
    buf = io.BytesIO()
    page_img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.getvalue()


def pages_to_zip_bytes(pages, depot, report_date):
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, p_img in enumerate(pages, start=1):
            p_bytes = pages_to_jpg_bytes(p_img)
            zf.writestr(f"{depot}_{report_date}_page_{idx}_of_{len(pages)}.jpg", p_bytes)
    zip_buf.seek(0)
    return zip_buf.getvalue()


def pages_to_pdf_bytes(pages):
    if not pages:
        return b""
    pdf_buf = io.BytesIO()
    first_page = pages[0].convert("RGB")
    other_pages = [p.convert("RGB") for p in pages[1:]]
    first_page.save(
        pdf_buf,
        format="PDF",
        save_all=True,
        append_images=other_pages,
        resolution=300.0,
    )
    pdf_buf.seek(0)
    return pdf_buf.getvalue()


def build_excel_bytes(depot, report_date, d_df, i_df, summary_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta_df = pd.DataFrame(
            [{"Depot": depot, "Date": format_display_date(report_date)}]
        )
        meta_df.to_excel(writer, sheet_name="Report_Details", index=False)
        d_df.to_excel(writer, sheet_name="Dispatch_OUT", index=False)
        i_df.to_excel(writer, sheet_name="Inward_IN", index=False)
        summary_df.to_excel(writer, sheet_name="Stock_Summary", index=False)
    output.seek(0)
    return output.getvalue()


def show_login():
    if st.session_state.get("session_expired_msg"):
        st.warning("15 minute tak inactive rehne ke kaaran session logout ho gaya hai. Kripya dobara login karein.")
        st.session_state.session_expired_msg = False

    render_brand_header()

    st.markdown(
        """
        <div class="mvs-hero">
            <div class="mvs-title">
                <span>MVS &amp; Wonder</span>
                <span class="mvs-badge"></span>
            </div>
            <div class="mvs-subtitle">Mangilal Vijayvargiya &amp; Sons &bull; Depot &amp; Distribution Operations</div>
        </div>
        <div class="get-started-heading">Get's Started</div>
        """,
        unsafe_allow_html=True,
    )

    _, mid_col, _ = st.columns([1, 1.5, 1])
    with mid_col:
        with st.form("login_form"):
            uid_input = st.text_input(
                "Login ID",
                placeholder="Enter your Login ID",
                label_visibility="collapsed",
            )
            pwd_input = st.text_input(
                "Password",
                type="password",
                placeholder="Enter Password",
                label_visibility="collapsed",
            )

            st.checkbox("Remember me?", value=False)
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            uid = uid_input.strip().lower().replace(" ", "")
            pwd = pwd_input.strip()
            if uid in USERS and USERS[uid][0] == pwd:
                st.session_state.user = (uid, USERS[uid][1])
                st.session_state.last_active_ts = time.time()
                st.rerun()
            else:
                st.error("Galat Login ID ya Password.")

    st.markdown(
        '<div class="mvs-footer">Copyright © All rights reserved</div>',
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="MVS & Wonder - Depot Report System", layout="wide")
    inject_mvs_wonder_theme_css()
    conn = get_connection()

    if "user" not in st.session_state:
        st.session_state.user = None

    check_and_refresh_session()

    if not st.session_state.user:
        show_login()
        return

    user_id, assigned_depot = st.session_state.user
    is_admin = assigned_depot is None
    role_text = (
        "ADMIN - ALL 8 DEPOTS"
        if is_admin
        else f"DEPOT INCHARGE - {assigned_depot}"
    )

    render_brand_header()

    st.markdown(
        f"""
        <div class="internal-topbar">
            <span class="internal-topbar-title">MVS &amp; Wonder &bull; DEPOT REPORT SYSTEM</span>
            <span class="internal-role-pill">{role_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-card-title">Report Details</div>', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([2.6, 1.8, 1.4])

    with r1:
        if is_admin:
            depot = st.selectbox("Depot", DEPOTS, label_visibility="collapsed")
        else:
            st.text_input("Depot", value=assigned_depot, disabled=True, label_visibility="collapsed")
            depot = assigned_depot

    with r2:
        if is_admin:
            selected_date = st.date_input("Date", value=date.today(), label_visibility="collapsed")
        else:
            selected_date = st.date_input(
                "Date", value=date.today(), disabled=True, label_visibility="collapsed"
            )
        report_date = str(selected_date)

    db_p_op, db_pl_op, db_x_op = load_meta(conn, depot, report_date)

    with r3:
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.user = None
            st.session_state.last_active_ts = None
            st.rerun()

    if is_admin:
        with st.expander("ADMIN IMPORT EXCEL", expanded=False):
            imp_file = st.file_uploader(
                "Upload Excel (.xlsx)",
                type=["xlsx"],
                key="admin_excel_uploader",
            )
            if st.button("IMPORT EXCEL"):
                if imp_file is not None:
                    d_cnt, i_cnt = import_excel_file(
                        conn, imp_file, depot, report_date, is_admin, user_id
                    )
                    st.success(
                        f"Import complete: Party entries sent for approval ({d_cnt}), Inward ({i_cnt}) saved."
                    )
                    st.rerun()
                else:
                    st.warning("Pehle Excel (.xlsx) file select karein.")

    tab1, tab2, tab3 = st.tabs(
        ["1. Dispatch / OUT", "2. Inward Trucks / IN", "3. Brand Stock Summary"]
    )

    with tab1:
        if is_admin:
            st.markdown(
                '<div class="section-card-title">Add Party Dispatch Entry (Admin Only - Goes for Depot Incharge Approval)</div>',
                unsafe_allow_html=True,
            )
            with st.form("party_dispatch_form", clear_on_submit=True):
                d1, d2, d3, d4, d5 = st.columns([3, 1, 1.5, 2, 1.5])
                party = d1.text_input("Party", placeholder="Party name")
                bag_val = d2.number_input("Bag", min_value=1, step=1, value=1)
                brand = d3.selectbox("Brand", PRODUCTS, key="d_brand")
                truck = d4.text_input("Truck", placeholder="Truck no")
                add_d = d5.form_submit_button("SEND FOR APPROVAL", use_container_width=True)

            if add_d:
                if not party.strip():
                    st.warning("Party ka naam enter karein.")
                else:
                    submit_party_for_approval(
                        conn, depot, report_date, party, bag_val, brand, truck, user_id
                    )
                    st.success("Party entry bhej di gayi hai. Depot Incharge ke Approve karne ke baad save hogi.")
                    st.rerun()

            with st.container(border=True):
                st.markdown("##### Pending Party Entries (Awaiting Depot Incharge Approval)")
                pend_rows_admin = pd.read_sql_query(
                    """
                    SELECT id, report_date AS Date, party AS Party, bag AS Bag, brand AS Brand, truck AS Truck, status AS Status
                    FROM pending_party_entries
                    WHERE depot = ? AND report_date = ? AND status = 'PENDING'
                    ORDER BY id DESC
                    """,
                    conn,
                    params=(depot, report_date),
                )

                if pend_rows_admin.empty:
                    st.info("Is date ke liye koi pending party entry nahi hai.")
                else:
                    ap_h1, ap_h2, ap_h3, ap_h4, ap_h5, ap_h6, ap_h7 = st.columns(
                        [1.2, 2.2, 0.9, 1.1, 1.5, 1.1, 1.2]
                    )
                    ap_h1.markdown("**Date**")
                    ap_h2.markdown("**Party**")
                    ap_h3.markdown("**Bag**")
                    ap_h4.markdown("**Brand**")
                    ap_h5.markdown("**Truck**")
                    ap_h6.markdown("**Status**")
                    ap_h7.markdown("**Delete**")

                    for row_idx, (_, prow) in enumerate(pend_rows_admin.iterrows()):
                        p_id = int(prow["id"])
                        row_shade = "#ECFDF5" if row_idx % 2 == 0 else "#E0F2FE"
                        c_dt, c_pt, c_bg, c_br, c_tr, c_st, c_dl = st.columns(
                            [1.2, 2.2, 0.9, 1.1, 1.5, 1.1, 1.2]
                        )
                        c_dt.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Date"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_pt.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Party"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_bg.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Bag"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_br.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Brand"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_tr.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Truck"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_st.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Status"]}</div>',
                            unsafe_allow_html=True,
                        )
                        if c_dl.button("Delete", key=f"del_pend_{p_id}", use_container_width=True):
                            delete_pending_by_id(conn, p_id, depot, report_date)
                            st.success(f"Pending entry ({prow['Party']} - {prow['Truck']}) delete ho gayi.")
                            st.rerun()

        else:
            with st.container(border=True):
                st.markdown("#### Approve Party Entries (Depot Incharge Only)")
                pend_rows = pd.read_sql_query(
                    """
                    SELECT id, report_date AS Date, party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
                    FROM pending_party_entries
                    WHERE depot = ? AND report_date = ? AND status = 'PENDING'
                    ORDER BY id DESC
                    """,
                    conn,
                    params=(depot, report_date),
                )

                if pend_rows.empty:
                    st.info("Is date ke liye koi pending party entry nahi hai.")
                else:
                    ph1, ph2, ph3, ph4, ph5, ph6 = st.columns([1.4, 2.6, 1.0, 1.2, 1.8, 1.4])
                    ph1.markdown("**Date**")
                    ph2.markdown("**Party**")
                    ph3.markdown("**Bag**")
                    ph4.markdown("**Brand**")
                    ph5.markdown("**Truck**")
                    ph6.markdown("**Approve**")

                    for row_idx, (_, prow) in enumerate(pend_rows.iterrows()):
                        p_id = int(prow["id"])
                        row_shade = "#ECFDF5" if row_idx % 2 == 0 else "#E0F2FE"
                        c_dt, c_pt, c_bg, c_br, c_tr, c_ap = st.columns([1.4, 2.6, 1.0, 1.2, 1.8, 1.4])
                        c_dt.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Date"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_pt.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Party"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_bg.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Bag"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_br.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Brand"]}</div>',
                            unsafe_allow_html=True,
                        )
                        c_tr.markdown(
                            f'<div style="background:{row_shade};color:#000000;padding:4px 6px;border-radius:4px;width:100%;font-weight:700;">{prow["Truck"]}</div>',
                            unsafe_allow_html=True,
                        )
                        clicked_approve = c_ap.button(
                            "Approve", key=f"approve_btn_{p_id}", use_container_width=True
                        )

                        if clicked_approve:
                            if approve_pending_entry(conn, p_id, depot, report_date, user_id):
                                st.success(f"{prow['Party']} ({prow['Truck']}) approve ho kar save ho gayi.")
                                st.rerun()
                            else:
                                st.error("Entry approve nahi ho saki.")

        st.markdown(
            '<div class="section-card-title">Approved & Saved Dispatch Entries (Latest Top)</div>',
            unsafe_allow_html=True,
        )
        d_rows = pd.read_sql_query(
            """
            SELECT id, report_date AS Date, party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
            FROM dispatch_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id DESC
            """,
            conn,
            params=(depot, report_date),
        )

        if d_rows.empty:
            st.info("Is date ke liye koi approved dispatch entry nahi hai.")
        else:
            if is_admin:
                dh1, dh2, dh3, dh4, dh5, dh6 = st.columns([1.4, 2.6, 1.0, 1.2, 1.8, 1.4])
                dh1.markdown("**Date**")
                dh2.markdown("**Party**")
                dh3.markdown("**Bag**")
                dh4.markdown("**Brand**")
                dh5.markdown("**Truck**")
                dh6.markdown("**Delete**")

                for _, drow in d_rows.iterrows():
                    d_id = int(drow["id"])
                    c_dt, c_pt, c_bg, c_br, c_tr, c_dl = st.columns([1.4, 2.6, 1.0, 1.2, 1.8, 1.4])
                    c_dt.write(drow["Date"])
                    c_pt.write(drow["Party"])
                    c_bg.write(str(drow["Bag"]))
                    c_br.write(drow["Brand"])
                    c_tr.write(drow["Truck"])
                    if c_dl.button("Delete", key=f"del_disp_{d_id}", use_container_width=True):
                        delete_dispatch_by_id(conn, d_id, depot, report_date)
                        st.rerun()
            else:
                st.dataframe(
                    d_rows[["Date", "Party", "Bag", "Brand", "Truck"]],
                    use_container_width=True,
                    hide_index=True,
                )

    with tab2:
        st.markdown('<div class="section-card-title">Add Inward Truck / In</div>', unsafe_allow_html=True)
        with st.form("inward_form", clear_on_submit=True):
            i1, i2, i3, i4, i5 = st.columns([2, 1, 1.5, 3, 1.5])
            in_truck = i1.text_input("Truck", placeholder="Truck no", key="i_truck")
            in_bag = i2.number_input("Bag", min_value=1, step=1, value=1, key="i_bag")
            in_brand = i3.selectbox("Brand", PRODUCTS, key="i_brand")
            roadline = i4.text_input("RoadLine", placeholder="RoadLine / From")
            add_i = i5.form_submit_button("ADD INWARD", use_container_width=True)

        if add_i:
            if not in_truck.strip():
                st.warning("Truck number enter karein.")
            else:
                load_meta(conn, depot, report_date)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO inward_entries (depot, report_date, truck, bag, brand, roadline)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (depot, report_date, in_truck.strip(), int(in_bag), in_brand, roadline.strip()),
                )
                conn.commit()
                st.rerun()

        i_rows = pd.read_sql_query(
            """
            SELECT id, report_date AS Date, truck AS Truck, bag AS Bag, brand AS Brand, roadline AS RoadLine
            FROM inward_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id DESC
            """,
            conn,
            params=(depot, report_date),
        )

        if i_rows.empty:
            st.info("Is date ke liye koi inward entry nahi hai.")
        else:
            if is_admin:
                ih1, ih2, ih3, ih4, ih5, ih6 = st.columns([1.4, 2.0, 1.0, 1.2, 2.4, 1.4])
                ih1.markdown("**Date**")
                ih2.markdown("**Truck**")
                ih3.markdown("**Bag**")
                ih4.markdown("**Brand**")
                ih5.markdown("**RoadLine**")
                ih6.markdown("**Delete**")

                for _, irow in i_rows.iterrows():
                    i_id = int(irow["id"])
                    c_dt, c_tr, c_bg, c_br, c_rl, c_dl = st.columns([1.4, 2.0, 1.0, 1.2, 2.4, 1.4])
                    c_dt.write(irow["Date"])
                    c_tr.write(irow["Truck"])
                    c_bg.write(str(irow["Bag"]))
                    c_br.write(irow["Brand"])
                    c_rl.write(irow["RoadLine"])
                    if c_dl.button("Delete", key=f"del_inw_{i_id}", use_container_width=True):
                        delete_inward_by_id(conn, i_id, depot, report_date)
                        st.rerun()
            else:
                st.dataframe(
                    i_rows[["Date", "Truck", "Bag", "Brand", "RoadLine"]],
                    use_container_width=True,
                    hide_index=True,
                )

    with tab3:
        st.markdown(
            '<div class="section-card-title">BRAND STOCK SUMMARY - ADMIN EDIT OP-ST</div>'
            if is_admin
            else '<div class="section-card-title">BRAND STOCK SUMMARY - OP-ST CARRIED FORWARD</div>',
            unsafe_allow_html=True,
        )

        with st.form("meta_form"):
            m1, m2, m3 = st.columns(3)
            p_op = m1.number_input(
                "Wonder PPC OP-ST", value=db_p_op, step=1, disabled=not is_admin
            )
            pl_op = m2.number_input(
                "Wonder PLUS OP-ST", value=db_pl_op, step=1, disabled=not is_admin
            )
            x_op = m3.number_input(
                "Wonder Xtreme OP-ST", value=db_x_op, step=1, disabled=not is_admin
            )
            save_btn = st.form_submit_button("Save OP-ST")

        if save_btn:
            save_meta(
                conn,
                depot,
                report_date,
                int(p_op),
                int(pl_op),
                int(x_op),
                is_admin,
            )
            st.success("OP-ST save ho gaya.")
            st.rerun()

        summary_df = compute_summary_rows(
            conn, depot, report_date, int(p_op), int(pl_op), int(x_op)
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # ========================================================
    # REPORT GENERATE, PRINT & EXPORT SECTION (DATE SELECTABLE)
    # ========================================================
    st.divider()
    st.markdown('<div class="section-card-title">Generate & Print Report</div>', unsafe_allow_html=True)

    gen_c1, gen_c2 = st.columns([2, 4])
    with gen_c1:
        if is_admin:
            gen_date_input = st.date_input(
                "Select Report Date to Generate",
                value=selected_date,
                key="report_generate_date",
            )
        else:
            gen_date_input = st.date_input(
                "Select Report Date to Generate",
                value=date.today(),
                disabled=True,
                key="report_generate_date",
            )
        gen_date = str(gen_date_input)

    gen_p_op, gen_pl_op, gen_x_op = load_meta(conn, depot, gen_date)

    d_df_gen = pd.read_sql_query(
        """
        SELECT party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
        FROM dispatch_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id DESC
        """,
        conn,
        params=(depot, gen_date),
    )
    i_df_gen = pd.read_sql_query(
        """
        SELECT truck AS Truck, bag AS Bag, brand AS Brand, roadline AS RoadLine
        FROM inward_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id DESC
        """,
        conn,
        params=(depot, gen_date),
    )
    summary_df_gen = compute_summary_rows(
        conn, depot, gen_date, gen_p_op, gen_pl_op, gen_x_op
    )

    a4_pages = build_a4_pages(
        depot, gen_date, d_df_gen, i_df_gen, summary_df_gen
    )

    with gen_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"**Report Date:** {format_display_date(gen_date)} ({gen_date}) | "
            f"**Depot:** {depot} | **A4 Pages:** {len(a4_pages)}"
        )

    b_print, b_excel, b_jpg, b_pdf = st.columns([1.4, 1.4, 1.5, 1.4])

    with b_print:
        st.markdown(
            """
            <button onclick="window.print()" style="width:100%;padding:0.45rem 0.75rem;background-color:#0284C7;color:#FFFFFF;border:1.5px solid #0369A1;border-radius:8px;font-weight:700;cursor:pointer;">
                Print Report
            </button>
            """,
            unsafe_allow_html=True,
        )

    with b_excel:
        excel_bytes = build_excel_bytes(
            depot, gen_date, d_df_gen, i_df_gen, summary_df_gen
        )
        st.download_button(
            label="Export Excel",
            data=excel_bytes,
            file_name=f"{depot}_{gen_date}_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with b_jpg:
        if len(a4_pages) == 1:
            st.download_button(
                label="Export JPG (A4)",
                data=pages_to_jpg_bytes(a4_pages[0]),
                file_name=f"{depot}_{gen_date}_A4_page_1.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )
        else:
            st.download_button(
                label=f"Export JPG ({len(a4_pages)} Pages ZIP)",
                data=pages_to_zip_bytes(a4_pages, depot, gen_date),
                file_name=f"{depot}_{gen_date}_A4_pages.zip",
                mime="application/zip",
                use_container_width=True,
            )

    with b_pdf:
        st.download_button(
            label="Export PDF (A4)",
            data=pages_to_pdf_bytes(a4_pages),
            file_name=f"{depot}_{gen_date}_A4_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
