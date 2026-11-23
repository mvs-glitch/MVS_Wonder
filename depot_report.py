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
    css_code = """
    <style>
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
        padding-top: 2.8rem !important;
        padding-bottom: 2.2rem !important;
        max-width: 100%;
        background-color: #FFFFFF !important;
    }

    .brand-top-strip {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 18px;
        margin-top: 8px;
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 12px;
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
        .block-container {
            padding-top: 3.4rem !important;
        }
        .brand-top-strip {
            margin-top: 12px;
        }
        .mvs-brand-mark {
            font-size: 16px;
        }
        .mvs-title {
            font-size: 28px;
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
    """
    st.markdown(css_code, unsafe_allow_html=True)


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

            if not is_admin:
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


def fetch_dispatch_df(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, party, bag, brand, truck, approved_by
        FROM dispatch_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id ASC
        """,
        (depot, report_date),
    )
    rows = cur.fetchall()
    return pd.DataFrame(
        [
            {
                "ID": int(r[0]),
                "Party": str(r[1]),
                "Bag": int(r[2]),
                "Brand": str(r[3]),
                "Truck": str(r[4] or ""),
                "Approved By": str(r[5] or ""),
            }
            for r in rows
        ]
    )


def fetch_pending_df(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, party, bag, brand, truck, created_by, status
        FROM pending_party_entries
        WHERE depot = ? AND report_date = ? AND status = 'PENDING'
        ORDER BY id ASC
        """,
        (depot, report_date),
    )
    rows = cur.fetchall()
    return pd.DataFrame(
        [
            {
                "ID": int(r[0]),
                "Party": str(r[1]),
                "Bag": int(r[2]),
                "Brand": str(r[3]),
                "Truck": str(r[4] or ""),
                "Created By": str(r[5] or ""),
                "Status": str(r[6]),
            }
            for r in rows
        ]
    )


def fetch_inward_df(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, truck, bag, brand, roadline
        FROM inward_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id ASC
        """,
        (depot, report_date),
    )
    rows = cur.fetchall()
    return pd.DataFrame(
        [
            {
                "ID": int(r[0]),
                "Truck": str(r[1]),
                "Bag": int(r[2]),
                "Brand": str(r[3]),
                "RoadLine": str(r[4] or ""),
            }
            for r in rows
        ]
    )


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


def render_login_screen():
    st.markdown(
        """
        <div class="mvs-hero">
            <div class="mvs-title">Depot Stock &amp; Dispatch Portal</div>
            <div class="mvs-subtitle">Daily Opening Stock, Inward, Dispatch &amp; A4 Reporting</div>
        </div>
        <div class="get-started-heading">Sign in to continue</div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("session_expired_msg"):
        st.warning("Session expired due to 15 minutes of inactivity. Please sign in again.")
        st.session_state.session_expired_msg = False

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("User ID").strip().lower()
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            creds = USERS.get(username)
            if creds and creds[0] == password:
                st.session_state.user = username
                st.session_state.assigned_depot = creds[1]
                st.session_state.last_active_ts = time.time()
                st.session_state.report_date = date.today()
                st.rerun()
            else:
                st.error("Invalid User ID or Password.")


def main():
    st.set_page_config(
        page_title="MVS Wonder Cement - Depot Reporting",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_mvs_wonder_theme_css()
    render_brand_header()

    if "user" not in st.session_state:
        st.session_state.user = None
    if "report_date" not in st.session_state:
        st.session_state.report_date = date.today()

    check_and_refresh_session()

    if st.session_state.get("user") is None:
        render_login_screen()
        st.markdown('<div class="mvs-footer">Mangilal Vijayvargiya &amp; Sons | Wonder Cement</div>', unsafe_allow_html=True)
        return

    user_id = st.session_state.user
    assigned_depot = st.session_state.get("assigned_depot")
    # Keval admin ko date change karne ki authority hai
    is_admin = (user_id == "admin") and (assigned_depot is None)

    conn = get_connection()

    role_label = "ADMIN (Full Access & Date Control)" if is_admin else f"DEPOT USER ({assigned_depot} | Date Locked)"
    st.markdown(
        f"""
        <div class="internal-topbar">
            <div class="internal-topbar-title">Depot Operations &amp; Daily Stock Report</div>
            <div class="internal-role-pill">{role_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.5, 1.5, 1.5, 1])

    with ctrl1:
        if is_admin:
            selected_depot = st.selectbox("Depot", DEPOTS, index=0, key="admin_depot_select")
        else:
            selected_depot = assigned_depot
            st.text_input("Depot", value=str(selected_depot), disabled=True, key="locked_depot_view")

    with ctrl2:
        if is_admin:
            current_dt = st.session_state.get("report_date", date.today())
            if not isinstance(current_dt, date):
                current_dt = date.today()
            selected_date = st.date_input(
                "Report Date (Admin Only)",
                value=current_dt,
                key="admin_report_date_input",
            )
            st.session_state.report_date = selected_date
        else:
            # Non-admin users ke liye date hamesha aaj ki lock rahegi
            selected_date = date.today()
            st.session_state.report_date = selected_date
            st.text_input(
                "Report Date (Locked)",
                value=format_display_date(selected_date.strftime("%Y-%m-%d")),
                disabled=True,
                key="locked_date_view",
            )

    report_date_str = selected_date.strftime("%Y-%m-%d")
    p_op, pl_op, x_op = load_meta(conn, selected_depot, report_date_str)

    with ctrl3:
        st.metric("Active Date", format_display_date(report_date_str))

    with ctrl4:
        st.write("")
        if st.button("Logout", use_container_width=True, key="logout_btn"):
            st.session_state.user = None
            st.session_state.assigned_depot = None
            st.session_state.last_active_ts = None
            st.rerun()

    # Opening Stock Editor (Admin editable, Depot user read-only)
    st.markdown('<div class="section-card-title">Opening Stock (OP-ST)</div>', unsafe_allow_html=True)
    op1, op2, op3, op4 = st.columns([1, 1, 1, 1])
    with op1:
        new_p_op = st.number_input("PPC Opening", min_value=0, value=int(p_op), step=1, disabled=not is_admin, key="op_ppc")
    with op2:
        new_pl_op = st.number_input("PLUS Opening", min_value=0, value=int(pl_op), step=1, disabled=not is_admin, key="op_plus")
    with op3:
        new_x_op = st.number_input("Xtreme Opening", min_value=0, value=int(x_op), step=1, disabled=not is_admin, key="op_xtreme")
    with op4:
        st.write("")
        if is_admin:
            if st.button("Save Opening Stock", use_container_width=True, key="save_op_btn"):
                save_meta(conn, selected_depot, report_date_str, new_p_op, new_pl_op, new_x_op, is_admin)
                st.success("Opening stock saved.")
                st.rerun()
        else:
            st.caption("Only Admin can edit OP-ST.")

    p_op, pl_op, x_op = load_meta(conn, selected_depot, report_date_str)

    tab_dispatch, tab_inward, tab_summary, tab_export = st.tabs(
        ["Dispatch (OUT)", "Inward Trucks (IN)", "Stock Summary", "Export / Print"]
    )

    with tab_dispatch:
        st.markdown('<div class="section-card-title">Add Dispatch Entry</div>', unsafe_allow_html=True)
        with st.form("dispatch_entry_form", clear_on_submit=True):
            f1, f2, f3, f4 = st.columns([2.2, 1.1, 1.2, 1.5])
            with f1:
                party_name = st.text_input("Party Name")
            with f2:
                bag_qty = st.number_input("Bags", min_value=1, value=1, step=1)
            with f3:
                brand_sel = st.selectbox("Brand", PRODUCTS, index=0)
            with f4:
                truck_no = st.text_input("Truck No.")

            submit_label = "Add to Dispatch (OUT)" if is_admin else "Submit for Approval"
            if st.form_submit_button(submit_label, use_container_width=True):
                if not party_name.strip():
                    st.error("Please enter Party Name.")
                elif is_admin:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO dispatch_entries
                        (depot, report_date, party, bag, brand, truck, approved_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (selected_depot, report_date_str, party_name.strip(), int(bag_qty), brand_sel, truck_no.strip(), user_id),
                    )
                    conn.commit()
                    st.success("Dispatch entry added.")
                    st.rerun()
                else:
                    submit_party_for_approval(conn, selected_depot, report_date_str, party_name, int(bag_qty), brand_sel, truck_no, user_id)
                    st.success("Submitted to Pending Approval list.")
                    st.rerun()

        pending_df = fetch_pending_df(conn, selected_depot, report_date_str)
        if not pending_df.empty:
            st.markdown('<div class="section-card-title">Pending Dispatch Approvals</div>', unsafe_allow_html=True)
            for _, prow in pending_df.iterrows():
                pcol1, pcol2, pcol3 = st.columns([4.5, 1.2, 1.2])
                with pcol1:
                    st.write(
                        f"**{prow['Party']}** | {prow['Bag']} bags | {prow['Brand']} | Truck: {prow['Truck'] or '-'} *(by {prow['Created By']})*"
                    )
                with pcol2:
                    if is_admin:
                        if st.button("Approve", key=f"app_pend_{prow['ID']}", use_container_width=True):
                            if approve_pending_entry(conn, int(prow["ID"]), selected_depot, report_date_str, user_id):
                                st.success("Approved and moved to Dispatch.")
                                st.rerun()
                    else:
                        st.caption("Awaiting Admin")
                with pcol3:
                    if is_admin or prow["Created By"] == user_id:
                        if st.button("Delete", key=f"del_pend_{prow['ID']}", use_container_width=True):
                            delete_pending_by_id(conn, int(prow["ID"]), selected_depot, report_date_str)
                            st.rerun()

        d_df = fetch_dispatch_df(conn, selected_depot, report_date_str)
        st.markdown('<div class="section-card-title">Approved Dispatch Entries (OUT)</div>', unsafe_allow_html=True)
        if d_df.empty:
            st.info("No approved dispatch entries for this date and depot.")
        else:
            st.dataframe(d_df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
            if is_admin:
                del_d_id = st.selectbox(
                    "Select Dispatch Entry ID to Delete",
                    options=d_df["ID"].tolist(),
                    format_func=lambda x: f"#{x} - {d_df.loc[d_df['ID'] == x, 'Party'].values[0]} ({d_df.loc[d_df['ID'] == x, 'Bag'].values[0]} bags)",
                    key="del_dispatch_select",
                )
                if st.button("Delete Selected Dispatch Entry", key="del_dispatch_btn"):
                    delete_dispatch_by_id(conn, int(del_d_id), selected_depot, report_date_str)
                    st.success("Dispatch entry deleted.")
                    st.rerun()

    with tab_inward:
        st.markdown('<div class="section-card-title">Add Inward Truck Entry (IN)</div>', unsafe_allow_html=True)
        with st.form("inward_entry_form", clear_on_submit=True):
            i1, i2, i3, i4 = st.columns([1.8, 1.1, 1.2, 2.0])
            with i1:
                in_truck = st.text_input("Truck No.")
            with i2:
                in_bag = st.number_input("Bags", min_value=1, value=1, step=1, key="in_bag_input")
            with i3:
                in_brand = st.selectbox("Brand", PRODUCTS, index=0, key="in_brand_select")
            with i4:
                in_roadline = st.text_input("RoadLine / Source")

            if st.form_submit_button("Add Inward (IN)", use_container_width=True):
                if not in_truck.strip():
                    st.error("Please enter Truck No.")
                else:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO inward_entries (depot, report_date, truck, bag, brand, roadline)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (selected_depot, report_date_str, in_truck.strip(), int(in_bag), in_brand, in_roadline.strip()),
                    )
                    conn.commit()
                    st.success("Inward entry added.")
                    st.rerun()

        i_df = fetch_inward_df(conn, selected_depot, report_date_str)
        st.markdown('<div class="section-card-title">Inward Truck Entries (IN)</div>', unsafe_allow_html=True)
        if i_df.empty:
            st.info("No inward entries for this date and depot.")
        else:
            st.dataframe(i_df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
            if is_admin:
                del_i_id = st.selectbox(
                    "Select Inward Entry ID to Delete",
                    options=i_df["ID"].tolist(),
                    format_func=lambda x: f"#{x} - {i_df.loc[i_df['ID'] == x, 'Truck'].values[0]} ({i_df.loc[i_df['ID'] == x, 'Bag'].values[0]} bags)",
                    key="del_inward_select",
                )
                if st.button("Delete Selected Inward Entry", key="del_inward_btn"):
                    delete_inward_by_id(conn, int(del_i_id), selected_depot, report_date_str)
                    st.success("Inward entry deleted.")
                    st.rerun()

        st.markdown('<div class="section-card-title">Import from Excel (.xlsx)</div>', unsafe_allow_html=True)
        uploaded_xl = st.file_uploader("Upload Excel file with Dispatch/OUT and/or Inward/IN sheets", type=["xlsx"], key="excel_uploader")
        if uploaded_xl is not None:
            if st.button("Import Excel Data", key="import_excel_btn"):
                imp_d, imp_i = import_excel_file(conn, uploaded_xl, selected_depot, report_date_str, is_admin, user_id)
                st.success(f"Imported {imp_d} dispatch row(s) and {imp_i} inward row(s).")
                st.rerun()

    d_df = fetch_dispatch_df(conn, selected_depot, report_date_str)
    i_df = fetch_inward_df(conn, selected_depot, report_date_str)
    summary_df = compute_summary_rows(conn, selected_depot, report_date_str, p_op, pl_op, x_op)

    with tab_summary:
        st.markdown('<div class="section-card-title">Brand Stock Summary</div>', unsafe_allow_html=True)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with tab_export:
        st.markdown('<div class="section-card-title">Download &amp; Preview A4 Report</div>', unsafe_allow_html=True)
        d_export = d_df[["Party", "Bag", "Brand", "Truck"]] if not d_df.empty else pd.DataFrame(columns=["Party", "Bag", "Brand", "Truck"])
        i_export = i_df[["Truck", "Bag", "Brand", "RoadLine"]] if not i_df.empty else pd.DataFrame(columns=["Truck", "Bag", "Brand", "RoadLine"])

        pages = build_a4_pages(selected_depot, report_date_str, d_export, i_export, summary_df)
        pdf_bytes = pages_to_pdf_bytes(pages)
        zip_bytes = pages_to_zip_bytes(pages, selected_depot, report_date_str)
        excel_bytes = build_excel_bytes(selected_depot, report_date_str, d_export, i_export, summary_df)

        ex1, ex2, ex3 = st.columns(3)
        with ex1:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"{selected_depot}_{report_date_str}_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with ex2:
            st.download_button(
                "Download JPGs (ZIP)",
                data=zip_bytes,
                file_name=f"{selected_depot}_{report_date_str}_Pages.zip",
                mime="application/zip",
                use_container_width=True,
            )
        with ex3:
            st.download_button(
                "Download Excel",
                data=excel_bytes,
                file_name=f"{selected_depot}_{report_date_str}_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        for idx, p_img in enumerate(pages, start=1):
            st.image(p_img, caption=f"Page {idx} of {len(pages)}", use_container_width=True)

    st.markdown('<div class="mvs-footer">Mangilal Vijayvargiya &amp; Sons | Wonder Cement</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
