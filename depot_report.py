import io
import os
import sqlite3
import zipfile
from datetime import date, datetime
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, "depot_data.db")

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


def get_fonts(title_size=44, section_size=30, body_size=26, small_size=24):
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
        (depot, report_date, report_no or "85"),
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
        return row[0] or "85", int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)
    return "85", 0, 0, 0


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
            (report_no or "85", p_op, pl_op, x_op, depot, report_date),
        )
    else:
        cur.execute(
            """
            UPDATE report_meta
            SET report_no = ?
            WHERE depot = ? AND report_date = ?
            """,
            (report_no or "85", depot, report_date),
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


def _draw_row(draw, x_left, y, col_widths, row_h, values, font, bold_last=False):
    cur_x = x_left
    for idx, w in enumerate(col_widths):
        box = (cur_x, y, cur_x + w, y + row_h)
        draw.rectangle(box, outline="#000000", width=2, fill="#ffffff")
        cell_font = font
        _draw_centered_text(draw, box, values[idx], cell_font, fill="#000000")
        cur_x += w


def _new_a4_page(depot, report_no, disp_date, page_num, total_pages_hint=None):
    f_title, f_sec, f_body, f_small = get_fonts()
    img = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)

    margin_x = 90
    top_y = 90
    table_w = A4_WIDTH - (2 * margin_x)

    # Top Depot Header Box
    depot_h = 84
    draw.rectangle(
        (margin_x, top_y, margin_x + table_w, top_y + depot_h),
        outline="#000000",
        width=3,
        fill="#ffffff",
    )
    page_suffix = f"  (Page {page_num})" if page_num > 1 else ""
    _draw_centered_text(
        draw,
        (margin_x, top_y, margin_x + table_w, top_y + depot_h),
        f"DEPOT : {depot}{page_suffix}",
        f_title,
        fill="#000000",
    )

    # Report No & Date Sub-header Box
    meta_y = top_y + depot_h
    meta_h = 74
    w_lbl = int(table_w * 0.25)
    w_no = int(table_w * 0.22)
    w_dt = table_w - w_lbl - w_no

    draw.rectangle((margin_x, meta_y, margin_x + w_lbl, meta_y + meta_h), outline="#000000", width=3, fill="#ffffff")
    _draw_centered_text(draw, (margin_x, meta_y, margin_x + w_lbl, meta_y + meta_h), "Report No", f_sec)

    draw.rectangle((margin_x + w_lbl, meta_y, margin_x + w_lbl + w_no, meta_y + meta_h), outline="#000000", width=3, fill="#ffffff")
    _draw_centered_text(draw, (margin_x + w_lbl, meta_y, margin_x + w_lbl + w_no, meta_y + meta_h), str(report_no), f_sec)

    draw.rectangle((margin_x + w_lbl + w_no, meta_y, margin_x + table_w, meta_y + meta_h), outline="#000000", width=3, fill="#ffffff")
    _draw_centered_text(
        draw,
        (margin_x + w_lbl + w_no, meta_y, margin_x + table_w, meta_y + meta_h),
        f"Date : {disp_date}",
        f_sec,
    )

    return img, draw, margin_x, table_w, meta_y + meta_h


def build_a4_pages(depot, report_no, report_date, d_df, i_df, summary_df):
    f_title, f_sec, f_body, f_small = get_fonts()
    disp_date = format_display_date(report_date)
    bottom_limit = A4_HEIGHT - 100

    pages = []
    page_num = 1
    img, draw, x_left, table_w, y = _new_a4_page(depot, report_no, disp_date, page_num)

    section_h = 64
    header_h = 58
    row_h = 54
    gap_h = 44

    # 4-column layout matching reference image
    col4 = [
        int(table_w * 0.34),
        int(table_w * 0.18),
        int(table_w * 0.18),
        table_w - int(table_w * 0.34) - int(table_w * 0.18) - int(table_w * 0.18),
    ]

    # 5-column layout for Brand Stock Summary
    col5 = [
        int(table_w * 0.32),
        int(table_w * 0.17),
        int(table_w * 0.17),
        int(table_w * 0.17),
        table_w - int(table_w * 0.32) - (3 * int(table_w * 0.17)),
    ]

    def ensure_space(needed_h):
        nonlocal img, draw, y, page_num
        if y + needed_h > bottom_limit:
            pages.append(img)
            page_num += 1
            img, draw, x_left, table_w, y = _new_a4_page(depot, report_no, disp_date, page_num)

    # ---------------- DISPATCH (OUT) ----------------
    ensure_space(gap_h + section_h + header_h + row_h)
    y += gap_h
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#000000", width=2, fill="#ffffff")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "DISPATCH (OUT)", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col4, header_h, ["Party", "Bag", "Brand", "Truck"], f_sec)
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
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#000000", width=2, fill="#ffffff")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "INWARD TRUCKS (IN)", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col4, header_h, ["Truck", "Bag", "Brand", "RoadLine"], f_sec)
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
    draw.rectangle((x_left, y, x_left + table_w, y + section_h), outline="#000000", width=2, fill="#ffffff")
    _draw_centered_text(draw, (x_left, y, x_left + table_w, y + section_h), "BRAND STOCK SUMMARY", f_sec)
    y += section_h

    _draw_row(draw, x_left, y, col5, header_h, ["Brand", "OP-ST", "In", "Out", "Total"], f_sec)
    y += header_h

    for _, r in summary_df.iterrows():
        _draw_row(
            draw,
            x_left,
            y,
            col5,
            row_h,
            [r["Brand"], r["OP-ST"], r["In"], r["Out"], r["Total"]],
            f_body,
        )
        y += row_h

    pages.append(img)
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
            zf.writestr(f"{depot}_{report_date}_page_{idx}.jpg", p_bytes)
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


def build_excel_bytes(depot, report_no, report_date, d_df, i_df, summary_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta_df = pd.DataFrame(
            [{"Depot": depot, "Report No": report_no, "Date": format_display_date(report_date)}]
        )
        meta_df.to_excel(writer, sheet_name="Report_Details", index=False)
        d_df.to_excel(writer, sheet_name="Dispatch_OUT", index=False)
        i_df.to_excel(writer, sheet_name="Inward_IN", index=False)
        summary_df.to_excel(writer, sheet_name="Stock_Summary", index=False)
    output.seek(0)
    return output.getvalue()


def show_login():
    st.markdown(
        """
        <div style="background-color:#0d47a1;padding:12px 20px;border-radius:6px;margin-bottom:18px;">
            <span style="color:white;font-size:22px;font-weight:bold;">DEPOT REPORT SYSTEM</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
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


def main():
    st.set_page_config(page_title="Depot Report System", layout="wide")
    conn = get_connection()

    if "user" not in st.session_state:
        st.session_state.user = None

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
            bag_val = d2.number_input("Bag", min_value=1, step=1, value=1)
            brand = d3.selectbox("Brand", PRODUCTS, key="d_brand")
            truck = d4.text_input("Truck", placeholder="Truck no")
            add_d = d5.form_submit_button("ADD DISPATCH", use_container_width=True)

        if add_d:
            if not party.strip():
                st.warning("Party ka naam enter karein.")
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO dispatch_entries (depot, report_date, party, bag, brand, truck)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (depot, report_date, party.strip(), int(bag_val), brand, truck.strip()),
                )
                conn.commit()
                st.rerun()

        d_df = pd.read_sql_query(
            """
            SELECT id AS ID, report_date AS Date, party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
            FROM dispatch_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id ASC
            """,
            conn,
            params=(depot, report_date),
        )
        st.dataframe(d_df, use_container_width=True, hide_index=True)

        del_c1, del_c2 = st.columns([2, 6])
        del_d_id = del_c1.number_input(
            "Delete Dispatch ID (#)", min_value=0, step=1, value=0, key="del_d_id"
        )
        if del_c2.button("DELETE DISPATCH"):
            if del_d_id > 0:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM dispatch_entries WHERE id = ? AND depot = ? AND report_date = ?",
                    (int(del_d_id), depot, report_date),
                )
                conn.commit()
                st.rerun()

    with tab2:
        st.markdown("#### Add Inward Truck / In")
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

        i_df = pd.read_sql_query(
            """
            SELECT id AS ID, truck AS Truck, bag AS Bag, brand AS Brand, roadline AS RoadLine
            FROM inward_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id ASC
            """,
            conn,
            params=(depot, report_date),
        )
        st.dataframe(i_df, use_container_width=True, hide_index=True)

        idel_c1, idel_c2 = st.columns([2, 6])
        del_i_id = idel_c1.number_input(
            "Delete Inward ID (#)", min_value=0, step=1, value=0, key="del_i_id"
        )
        if idel_c2.button("DELETE INWARD"):
            if del_i_id > 0:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM inward_entries WHERE id = ? AND depot = ? AND report_date = ?",
                    (int(del_i_id), depot, report_date),
                )
                conn.commit()
                st.rerun()

    with tab3:
        st.markdown(
            "#### BRAND STOCK SUMMARY - ADMIN EDIT OP-ST"
            if is_admin
            else "#### BRAND STOCK SUMMARY - OP-ST LOCKED"
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
            save_btn = st.form_submit_button("Save Report Details / OP-ST")

        if save_btn:
            save_meta(
                conn,
                depot,
                report_date,
                report_no,
                int(p_op),
                int(pl_op),
                int(x_op),
                is_admin,
            )
            st.success("Report details save ho gayi.")
            st.rerun()

        summary_df = compute_summary_rows(
            conn, depot, report_date, int(p_op), int(pl_op), int(x_op)
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.divider()

    d_df_all = pd.read_sql_query(
        """
        SELECT party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
        FROM dispatch_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id ASC
        """,
        conn,
        params=(depot, report_date),
    )
    i_df_all = pd.read_sql_query(
        """
        SELECT truck AS Truck, bag AS Bag, brand AS Brand, roadline AS RoadLine
        FROM inward_entries
        WHERE depot = ? AND report_date = ?
        ORDER BY id ASC
        """,
        conn,
        params=(depot, report_date),
    )
    summary_df_all = compute_summary_rows(
        conn, depot, report_date, db_p_op, db_pl_op, db_x_op
    )

    a4_pages = build_a4_pages(
        depot, report_no, report_date, d_df_all, i_df_all, summary_df_all
    )

    b_left, b_excel, b_jpg, b_pdf = st.columns([4.2, 1.4, 1.5, 1.4])
    with b_left:
        st.markdown(
            f"**User:** {user_id} | **Depot:** {depot} | **Date:** {report_date} | "
            f"**A4 Pages:** {len(a4_pages)}"
        )

    with b_excel:
        excel_bytes = build_excel_bytes(
            depot, report_no, report_date, d_df_all, i_df_all, summary_df_all
        )
        st.download_button(
            label="Export Excel",
            data=excel_bytes,
            file_name=f"{depot}_{report_date}_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with b_jpg:
        if len(a4_pages) == 1:
            st.download_button(
                label="Export JPG (A4)",
                data=pages_to_jpg_bytes(a4_pages[0]),
                file_name=f"{depot}_{report_date}_A4_page_1.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )
        else:
            st.download_button(
                label=f"Export JPG ({len(a4_pages)} Pages ZIP)",
                data=pages_to_zip_bytes(a4_pages, depot, report_date),
                file_name=f"{depot}_{report_date}_A4_pages.zip",
                mime="application/zip",
                use_container_width=True,
            )

    with b_pdf:
        st.download_button(
            label="Export PDF (A4)",
            data=pages_to_pdf_bytes(a4_pages),
            file_name=f"{depot}_{report_date}_A4_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
