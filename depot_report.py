import os
import sqlite3
from datetime import date
import pandas as pd
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


def compute_summary(conn, depot, report_date, p_op, pl_op, x_op):
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
    for label, key, op_val in [
        ("Wonder PPC", "PPC", p_op),
        ("Wonder PLUS", "PLUS", pl_op),
        ("Wonder Xtreme", "Xtreme", x_op),
    ]:
        in_val = in_map.get(key, 0)
        out_val = out_map.get(key, 0)
        total_val = op_val + in_val - out_val
        rows.append(
            {
                "Brand": label,
                "OP-ST": op_val,
                "In": in_val,
                "Out": out_val,
                "Total": total_val,
            }
        )

    return pd.DataFrame(rows)


def main():
    st.set_page_config(page_title="8-Depot Daily Report System", layout="wide")
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

        st.caption("Admin: admin / admin123")
        return

    user_id, assigned_depot = st.session_state.user
    is_admin = assigned_depot is None
    role_text = "ADMIN - ALL 8 DEPOTS" if is_admin else f"DEPOT INCHARGE - {assigned_depot}"

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("DEPOT REPORT SYSTEM")
        st.caption(f"{role_text} | User: {user_id}")
    with top_right:
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    st.divider()
    st.subheader("Report Details")

    c1, c2, c3 = st.columns(3)
    with c1:
        if is_admin:
            depot = st.selectbox("Depot", DEPOTS)
        else:
            st.text_input("Depot", value=assigned_depot, disabled=True)
            depot = assigned_depot

    with c2:
        selected_date = st.date_input("Date", value=date.today())
        report_date = str(selected_date)

    default_r_no, db_p_op, db_pl_op, db_x_op = load_meta(conn, depot, report_date)

    with c3:
        report_no = st.text_input("Report No", value=default_r_no)

    ensure_meta(conn, depot, report_date, report_no)

    tab1, tab2, tab3 = st.tabs(
        ["1. Dispatch / OUT", "2. Inward Trucks / IN", "3. Brand Stock Summary"]
    )

    with tab1:
        st.subheader("Add Dispatch / Outward")
        with st.form("dispatch_form", clear_on_submit=True):
            d1, d2, d3, d4 = st.columns([3, 1, 2, 2])
            party = d1.text_input("Party")
            bag_val = d2.number_input("Bag", min_value=1, step=1, value=1)
            brand = d3.selectbox("Brand", PRODUCTS, key="d_brand")
            truck = d4.text_input("Truck")
            add_d = st.form_submit_button("Add Dispatch")

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
                st.success("Dispatch entry save ho gayi.")
                st.rerun()

        d_df = pd.read_sql_query(
            """
            SELECT id AS ID, party AS Party, bag AS Bag, brand AS Brand, truck AS Truck
            FROM dispatch_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id DESC
            """,
            conn,
            params=(depot, report_date),
        )
        st.dataframe(d_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="Export Dispatch CSV",
            data=d_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{depot}_{report_date}_dispatch.csv",
            mime="text/csv",
        )

    with tab2:
        st.subheader("Add Inward Truck / In")
        with st.form("inward_form", clear_on_submit=True):
            i1, i2, i3, i4 = st.columns([2, 1, 2, 3])
            in_truck = i1.text_input("Truck", key="i_truck")
            in_bag = i2.number_input("Bag", min_value=1, step=1, value=1, key="i_bag")
            in_brand = i3.selectbox("Brand", PRODUCTS, key="i_brand")
            roadline = i4.text_input("RoadLine")
            add_i = st.form_submit_button("Add Inward")

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
                st.success("Inward entry save ho gayi.")
                st.rerun()

        i_df = pd.read_sql_query(
            """
            SELECT id AS ID, truck AS Truck, bag AS Bag, brand AS Brand, roadline AS RoadLine
            FROM inward_entries
            WHERE depot = ? AND report_date = ?
            ORDER BY id DESC
            """,
            conn,
            params=(depot, report_date),
        )
        st.dataframe(i_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="Export Inward CSV",
            data=i_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{depot}_{report_date}_inward.csv",
            mime="text/csv",
        )

    with tab3:
        st.subheader(
            "Brand Stock Summary - Admin Edit OP-ST"
            if is_admin
            else "Brand Stock Summary - OP-ST Locked"
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

        summary_df = compute_summary(
            conn, depot, report_date, int(p_op), int(pl_op), int(x_op)
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="Export Summary CSV",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{depot}_{report_date}_summary.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
