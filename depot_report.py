import io
import os
import sqlite3
from datetime import date
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, "depot_data.db")

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


def get_fonts(title_size=18, section_size=14, body_size=12, small_size=11):
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
            report_no TEXT DEFAULT '',
            ppc_op INTEGER DEFAULT 0,
            plus_op INTEGER DEFAULT 0,
            xtreme_op INTEGER DEFAULT 0,
            PRIMARY KEY (depot, report_date)
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
            truck TEXT DEFAULT ''
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

    conn.commit()
    return conn


def ensure_meta(conn, depot, report_date, report_no):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO report_meta
        (depot, report_date, report_no, ppc_op, plus_op, xtreme_op)
        VALUES (?, ?, ?, 0, 0, 0)
        """,
        (depot, report_date, report_no or "84"),
    )
    conn.commit()


def load_meta(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT report_no, ppc_op, plus_op, xtreme_op
        FROM report_meta
        WHERE depot = ? AND report_date = ?
        """,
        (depot, report_date),
    )
    row = cur.fetchone()
    if row:
        return row[0] or "84", int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)
    return "84", 0, 0, 0


def save_meta(conn, depot, report_date, report_no, p_op, pl_op, x_op, is_admin):
    ensure_meta(conn, depot, report_date, report_no)
    cur = conn.cursor()
    if is_admin:
        cur.execute(
            """
            UPDATE report_meta
            SET report_no = ?, ppc_op = ?, plus_op = ?, xtreme_op = ?
            WHERE depot = ? AND report_date = ?
            """,
            (report_no or "84", p_op, pl_op, x_op, depot, report_date),
        )
    else:
        cur.execute(
            """
            UPDATE report_meta
            SET report_no = ?
            WHERE depot = ? AND report_date = ?
            """,
            (report_no or "84", depot, report_date),
        )
    conn.commit()


def clear_day_data(conn, depot, report_date):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM dispatch_entries WHERE depot = ? AND report_date = ?",
        (depot, report_date),
    )
    cur.execute(
        "DELETE FROM inward_entries WHERE depot = ? AND report_date = ?",
        (depot, report_date),
    )
    cur.execute(
        """
        UPDATE report_meta
        SET ppc_op = 0, plus_op = 0, xtreme_op = 0
        WHERE depot = ? AND report_date = ?
        """,
        (depot, report_date),
    )
    conn.commit()


def compute_summary_rows(conn, depot, report_date, p_op, pl_op, x_op):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT brand, COALESCE(SUM(bag), 0)
        FROM inward_entries
        WHERE depot = ? AND report_date = ?
        GROUP BY brand
        """,
        (depot, report_date),
    )
    in_map = {row[0]: int(row[1] or 0) for row in cur.fetchall()}

    cur.execute(
        """
        SELECT brand, COALESCE(SUM(bag), 0)
        FROM dispatch_entries
        WHERE depot = ? AND report_date = ?
        GROUP BY brand
        """,
        (depot, report_date),
    )
    out_map = {row[0]: int(row[1] or 0) for row in cur.fetchall()}

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
            "Brand": "TOTAL",
            "OP-ST": tot_op,
            "In": tot_in,
            "Out": tot_out,
            "Total": tot_bal,
        }
    )

    return pd.DataFrame(rows)


def build_excel_bytes(depot, report_no, report_date, d_df, i_df, summary_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta_df = pd.DataFrame(
            [{"Depot": depot, "Report No": report_no, "Date": report_date}]
        )
        meta_df.to_excel(writer, sheet_name="Report_Details", index=False)
        d_df.to_excel(writer, sheet_name="Dispatch_OUT", index=False)
        i_df.to_excel(writer, sheet_name="Inward_IN", index=False)
        summary_df.to_excel(writer, sheet_name="Stock_Summary", index=False)
    output.seek(0)
    return output.getvalue()


def build_jpg_bytes(depot, report_no, report_date, d_df, i_df, summary_df):
    f_title, f_sec, f_body, f_small = get_fonts()
    width = 1040
    line_h = 26
    est_height = 240 + (len(d_df) + len(i_df) + len(summary_df) + 12) * line_h
    height = max(680, est_height)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    draw.rectangle([15, 15, width - 15, 65], fill="#0d47a1")
    draw.text(
        (30, 28),
        f"{depot}  |  Date: {report_date}  |  No: {report_no}",
        fill="white",
        font=f_title,
    )
    y = 85

    draw.text((25, y), "1. DISPATCH / OUT", fill="#0d47a1", font=f_sec)
    y += 28
    draw.text(
        (25, y),
        "ID     Date          Party                         Bag      Brand      Truck",
        fill="#111111",
        font=f_small,
    )
    y += 22
    if d_df.empty:
        draw.text((25, y), "No dispatch entries.", fill="#666666", font=f_body)
        y += 26
    else:
        for _, r in d_df.iterrows():
            line = (
                f"{str(r['ID']):<6} "
                f"{str(r['Date']):<13} "
                f"{str(r['Party'])[:26]:<28} "
                f"{str(r['Bag']):<8} "
                f"{str(r['Brand']):<10} "
                f"{str(r['Truck'])[:16]}"
            )
            draw.text((25, y), line, fill="#222222", font=f_body)
            y += 24
        y += 6

    draw.text((25, y), "2. INWARD TRUCKS / IN", fill="#0d47a1", font=f_sec)
    y += 28
    draw.text(
        (25, y),
        "ID     Truck               Bag      Brand      RoadLine",
        fill="#111111",
        font=f_small,
    )
    y += 22
    if i_df.empty:
        draw.text((25, y), "No inward entries.", fill="#666666", font=f_body)
        y += 26
    else:
        for _, r in i_df.iterrows():
            line = (
                f"{str(r['ID']):<6} "
                f"{str(r['Truck'])[:18]:<20} "
                f"{str(r['Bag']):<8} "
                f"{str(r['Brand']):<10} "
                f"{str(r['RoadLine'])[:22]}"
            )
            draw.text((25, y), line, fill="#222222", font=f_body)
            y += 24
        y += 6

    draw.text((25, y), "3. BRAND STOCK SUMMARY", fill="#0d47a1", font=f_sec)
    y += 28
    draw.text(
        (25, y),
        "Brand               OP-ST         In          Out         Total",
        fill="#111111",
        font=f_small,
    )
    y += 22
    for _, r in summary_df.iterrows():
        line = (
            f"{str(r['Brand']):<18} "
            f"{str(r['OP-ST']):<12} "
            f"{str(r['In']):<12} "
            f"{str(r['Out']):<12} "
            f"{str(r['Total']):<12}"
        )
        draw.text((25, y), line, fill="#111111", font=f_body)
        y += 24

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf.getvalue()


def main():
    st.set_page_config(page_title="Depot Report System", layout="wide")
    conn = get_connection()

    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        st.title("DEPOT REPORT SYSTEM")
        st.subheader("Depot Agent Login")

        with st.form("login_form"):
            uid_input = st.text_input("Login ID")
            pwd_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("LOGIN")

        if submitted:
            uid = uid_input.strip().lower().replace(" ", "")
            pwd = pwd_input.strip()
            if uid in USERS and USERS[uid][0] == pwd:
                st.session_state.user = (uid, USERS[uid][1])
                st.rerun()
            else:
                st.error("Galat Login ID ya Password.")

        return

    user_id, assigned_depot = st.session_state.user
    is_admin = assigned_depot is None
    role_text = (
        "ADMIN - ALL 8 DEPOTS"
        if is_admin
        else f"DEPOT INCHARGE - {assigned_depot}"
    )

    st.markdown(
        f"""
        <div style="background-color:#0d47a1;padding:12px 20px;border-radius:6px;display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="color:white;font-size:22px;font-weight:bold;">DEPOT REPORT SYSTEM</span>
            <span style="color:#e3f2fd;font-size:13px;font-weight:bold;">{role_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Report Details")
    r1, r2, r3, r4, r5, r6 = st.columns([2, 1.3, 1.5, 1.3, 1.3, 1.2])

    with r1:
        if is_admin:
            depot = st.selectbox("Depot", DEPOTS, label_visibility="collapsed")
        else:
            st.text_input("Depot", value=assigned_depot, disabled=True, label_visibility="collapsed")
            depot = assigned_depot

    with r2:
        selected_date = st.date_input("Date", value=date.today(), label_visibility="collapsed")
        report_date = str(selected_date)

    default_r_no, db_p_op, db_pl_op, db_x_op = load_meta(conn, depot, report_date)

    with r3:
        report_no = st.text_input("Report No", value=default_r_no, label_visibility="collapsed")

    ensure_meta(conn, depot, report_date, report_no)

    with r4:
        if st.button("LOAD DATA", use_container_width=True):
            st.rerun()

    with r5:
        if st.button("CLEAR DAY", use_container_width=True):
            clear_day_data(conn, depot, report_date)
            st.success("Is din ka data clear ho gaya.")
            st.rerun()

    with r6:
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    tab1, tab2, tab3 = st.tabs(
        ["1. Dispatch / OUT", "2. Inward Trucks / IN", "3. Brand Stock Summary"]
    )

    with tab1:
        st.markdown("#### Add Dispatch / Outward")
        with st.form("dispatch_form", clear_on_submit=True):
            d1, d2, d3, d4, d5 = st.columns([3, 1, 1.5, 2, 1.5])
            party = d1.text_input("Party", placeholder="Party name")
            bag_val = d2.number_input
