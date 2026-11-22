import os
import sys
import sqlite3
import traceback
# import tkinter as tk
# from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta

from openpyxl import Workbook, load_workbook
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# APPLICATION SETTINGS
# ============================================================

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


# ============================================================
# FONT FUNCTION FOR JPG
# ============================================================

def get_fonts(title_size=15, section_size=13, body_size=11, small_size=10):

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

    bold_path = next(
        (p for p in bold_candidates if os.path.exists(p)),
        None
    )

    regular_path = next(
        (p for p in regular_candidates if os.path.exists(p)),
        None
    )

    if bold_path and regular_path:
        return (
            ImageFont.truetype(bold_path, title_size),
            ImageFont.truetype(bold_path, section_size),
            ImageFont.truetype(regular_path, body_size),
            ImageFont.truetype(regular_path, small_size),
        )

    fallback = ImageFont.load_default()

    return (
        fallback,
        fallback,
        fallback,
        fallback,
    )


# ============================================================
# MAIN APPLICATION
# ============================================================

class DepotControllerApp:

    def __init__(self, root):

        self.root = root

        self.root.title("8-Depot Daily Report System")
        self.root.geometry("420x280")
        self.root.minsize(420, 280)

        self.conn = None

        try:
            self.conn = sqlite3.connect(
                DB_FILE,
                timeout=10
            )

            self.conn.execute("PRAGMA foreign_keys = ON")

            self.init_db()

        except Exception as ex:

            messagebox.showerror(
                "Database Error",
                f"Database start nahi ho saka:\n\n{ex}"
            )

            raise

        self.active_frame = None

        self.show_login()


    # ========================================================
    # DATABASE
    # ========================================================

    def init_db(self):

        cur = self.conn.cursor()

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

        self.conn.commit()


    # ========================================================
    # SAFE DATABASE COMMIT
    # ========================================================

    def safe_commit(self):

        try:
            self.conn.commit()
            return True

        except Exception as ex:

            try:
                self.conn.rollback()
            except Exception:
                pass

            messagebox.showerror(
                "Database Error",
                f"Data save nahi hua:\n\n{ex}",
                parent=self.root
            )

            return False


    # ========================================================
    # CLEAR CURRENT FRAME
    # ========================================================

    def clear_container(self):

        if self.active_frame is not None:

            try:
                self.active_frame.destroy()
            except Exception:
                pass

            self.active_frame = None


    # ========================================================
    # LOGIN SCREEN
    # ========================================================

    def show_login(self):

        self.clear_container()

        self.root.geometry("430x300")
        self.root.resizable(False, False)

        self.root.title("Depot Agent Login")

        frame = tk.Frame(
            self.root,
            padx=25,
            pady=20
        )

        frame.pack(
            fill="both",
            expand=True
        )

        self.active_frame = frame

        tk.Label(
            frame,
            text="DEPOT REPORT SYSTEM",
            font=("Arial", 17, "bold"),
            fg="#0d47a1"
        ).pack(pady=(0, 5))

        tk.Label(
            frame,
            text="Depot Agent Login",
            font=("Arial", 11)
        ).pack(pady=(0, 18))

        form = tk.Frame(frame)
        form.pack()

        tk.Label(
            form,
            text="Login ID:",
            font=("Arial", 10)
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=7
        )

        user_entry = tk.Entry(
            form,
            width=25,
            font=("Arial", 10)
        )

        user_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=7
        )

        tk.Label(
            form,
            text="Password:",
            font=("Arial", 10)
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=7
        )

        pass_entry = tk.Entry(
            form,
            width=25,
            font=("Arial", 10),
            show="*"
        )

        pass_entry.grid(
            row=1,
            column=1,
            padx=10,
            pady=7
        )

        user_entry.focus_set()


        def do_login(event=None):

            uid = (
                user_entry.get()
                .strip()
                .lower()
                .replace(" ", "")
            )

            pwd = pass_entry.get().strip()

            if uid in USERS and USERS[uid][0] == pwd:

                self.show_dashboard(
                    uid,
                    USERS[uid][1]
                )

            else:

                messagebox.showerror(
                    "Login Failed",
                    "Galat Login ID ya Password.",
                    parent=self.root
                )

                pass_entry.delete(
                    0,
                    "end"
                )

                pass_entry.focus_set()


        pass_entry.bind(
            "<Return>",
            do_login
        )

        user_entry.bind(
            "<Return>",
            lambda e: pass_entry.focus_set()
        )


        tk.Button(
            frame,
            text="LOGIN",
            command=do_login,
            bg="#1565c0",
            fg="white",
            activebackground="#0d47a1",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            width=18,
            pady=7,
            cursor="hand2"
        ).pack(pady=15)

        tk.Label(
            frame,
            text="Admin: admin / admin123",
            font=("Arial", 8),
            fg="#777777"
        ).pack()


    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(
        self,
        user_id,
        assigned_depot
    ):

        self.clear_container()

        self.root.geometry("1200x760")
        self.root.resizable(True, True)

        is_admin = assigned_depot is None

        role_text = (
            "ADMIN - ALL 8 DEPOTS"
            if is_admin
            else f"DEPOT INCHARGE - {assigned_depot}"
        )

        self.root.title(
            f"Depot Report System | {role_text}"
        )

        container = tk.Frame(
            self.root,
            bg="#eef2f7"
        )

        container.pack(
            fill="both",
            expand=True
        )

        self.active_frame = container


        # ====================================================
        # TOP HEADER
        # ====================================================

        header = tk.Frame(
            container,
            bg="#0d47a1",
            height=55
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(False)

        tk.Label(
            header,
            text="DEPOT REPORT SYSTEM",
            bg="#0d47a1",
            fg="white",
            font=("Arial", 17, "bold")
        ).pack(
            side="left",
            padx=18
        )

        tk.Label(
            header,
            text=role_text,
            bg="#0d47a1",
            fg="#e3f2fd",
            font=("Arial", 10, "bold")
        ).pack(
            side="right",
            padx=18
        )


        # ====================================================
        # REPORT DETAILS
        # ====================================================

        top_frame = tk.LabelFrame(
            container,
            text=" Report Details ",
            padx=10,
            pady=8,
            bg="#eef2f7",
            font=("Arial", 10, "bold")
        )

        top_frame.pack(
            fill="x",
            padx=12,
            pady=8
        )


        tk.Label(
            top_frame,
            text="Depot:",
            bg="#eef2f7"
        ).grid(
            row=0,
            column=0,
            padx=5,
            sticky="w"
        )

        initial_depot = (
            assigned_depot
            if assigned_depot
            else DEPOTS[0]
        )

        depot_var = tk.StringVar(
            value=initial_depot
        )

        depot_state = (
            "disabled"
            if assigned_depot
            else "readonly"
        )

        depot_combo = ttk.Combobox(
            top_frame,
            textvariable=depot_var,
            values=DEPOTS,
            width=18,
            state=depot_state
        )

        depot_combo.grid(
            row=0,
            column=1,
            padx=5
        )


        tk.Label(
            top_frame,
            text="Report No:",
            bg="#eef2f7"
        ).grid(
            row=0,
            column=2,
            padx=5,
            sticky="w"
        )

        report_no_entry = tk.Entry(
            top_frame,
            width=10
        )

        report_no_entry.insert(
            0,
            "84"
        )

        report_no_entry.grid(
            row=0,
            column=3,
            padx=5
        )


        tk.Label(
            top_frame,
            text="Date:",
            bg="#eef2f7"
        ).grid(
            row=0,
            column=4,
            padx=5,
            sticky="w"
        )

        date_entry = tk.Entry(
            top_frame,
            width=14
        )

        date_entry.insert(
            0,
            str(date.today())
        )

        date_entry.grid(
            row=0,
            column=5,
            padx=5
        )


        # ====================================================
        # NOTEBOOK
        # ====================================================

        notebook = ttk.Notebook(
            container
        )

        notebook.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=4
        )

        tab_dispatch = tk.Frame(
            notebook,
            bg="white"
        )

        tab_inward = tk.Frame(
            notebook,
            bg="white"
        )

        tab_summary = tk.Frame(
            notebook,
            bg="white"
        )

        notebook.add(
            tab_dispatch,
            text="1. Dispatch / OUT"
        )

        notebook.add(
            tab_inward,
            text="2. Inward Trucks / IN"
        )

        notebook.add(
            tab_summary,
            text="3. Brand Stock Summary"
        )


        # ====================================================
        # BOTTOM
        # ====================================================

        bottom_frame = tk.Frame(
            container,
            bg="#eef2f7",
            pady=7
        )

        bottom_frame.pack(
            fill="x",
            padx=12
        )

        status_lbl = tk.Label(
            bottom_frame,
            text=f"User: {user_id}",
            bg="#eef2f7",
            fg="#2e7d32",
            font=("Arial", 9, "bold")
        )

        status_lbl.pack(
            side="left"
        )


        # ====================================================
        # CONTEXT
        # ====================================================

        def get_ctx():

            d = (
                assigned_depot
                if assigned_depot
                else depot_var.get().strip()
            )

            dt = date_entry.get().strip()

            return d, dt


        # ====================================================
        # ENSURE META
        # ====================================================

        def ensure_meta(d, dt):

            if not d or not dt:
                return False

            try:

                cur = self.conn.cursor()

                cur.execute(
                    """
                    INSERT OR IGNORE INTO report_meta
                    (
                        depot,
                        report_date,
                        report_no,
                        ppc_op,
                        plus_op,
                        xtreme_op
                    )
                    VALUES (?, ?, ?, 0, 0, 0)
                    """,
                    (
                        d,
                        dt,
                        report_no_entry.get().strip() or "84"
                    )
                )

                self.conn.commit()

                return True

            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Database Error",
                    f"Meta data save error:\n\n{ex}",
                    parent=self.root
                )

                return False


        # ====================================================
        # DISPATCH TAB
        # ====================================================

        d_form = tk.LabelFrame(
            tab_dispatch,
            text="Add Dispatch / Outward",
            padx=10,
            pady=10,
            bg="white",
            font=("Arial", 10, "bold")
        )

        d_form.pack(
            fill="x",
            padx=10,
            pady=10
        )


        tk.Label(
            d_form,
            text="Party:",
            bg="white"
        ).grid(
            row=0,
            column=0,
            padx=5
        )

        d_party = tk.Entry(
            d_form,
            width=23
        )

        d_party.grid(
            row=0,
            column=1,
            padx=5
        )


        tk.Label(
            d_form,
            text="Bag:",
            bg="white"
        ).grid(
            row=0,
            column=2,
            padx=5
        )

        d_bag = tk.Entry(
            d_form,
            width=10
        )

        d_bag.grid(
            row=0,
            column=3,
            padx=5
        )


        tk.Label(
            d_form,
            text="Brand:",
            bg="white"
        ).grid(
            row=0,
            column=4,
            padx=5
        )

        d_brand = ttk.Combobox(
            d_form,
            values=PRODUCTS,
            width=12,
            state="readonly"
        )

        d_brand.set(
            "PPC"
        )

        d_brand.grid(
            row=0,
            column=5,
            padx=5
        )


        tk.Label(
            d_form,
            text="Truck:",
            bg="white"
        ).grid(
            row=0,
            column=6,
            padx=5
        )

        d_truck = tk.Entry(
            d_form,
            width=17
        )

        d_truck.grid(
            row=0,
            column=7,
            padx=5
        )


        d_cols = (
            "ID",
            "Party",
            "Bag",
            "Brand",
            "Truck"
        )

        d_tree = ttk.Treeview(
            tab_dispatch,
            columns=d_cols,
            show="headings",
            height=14
        )

        d_tree.heading(
            "ID",
            text="#"
        )

        d_tree.column(
            "ID",
            width=55,
            anchor="center"
        )

        for c in (
            "Party",
            "Bag",
            "Brand",
            "Truck"
        ):

            d_tree.heading(
                c,
                text=c
            )

        d_tree.column(
            "Party",
            width=280
        )

        d_tree.column(
            "Bag",
            width=100,
            anchor="center"
        )

        d_tree.column(
            "Brand",
            width=150,
            anchor="center"
        )

        d_tree.column(
            "Truck",
            width=200
        )


        d_scroll = ttk.Scrollbar(
            tab_dispatch,
            orient="vertical",
            command=d_tree.yview
        )

        d_tree.configure(
            yscrollcommand=d_scroll.set
        )

        d_tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 0),
            pady=5
        )

        d_scroll.pack(
            side="right",
            fill="y",
            padx=(0, 10),
            pady=5
        )


        # ====================================================
        # INWARD TAB
        # ====================================================

        i_form = tk.LabelFrame(
            tab_inward,
            text="Add Inward Truck / In",
            padx=10,
            pady=10,
            bg="white",
            font=("Arial", 10, "bold")
        )

        i_form.pack(
            fill="x",
            padx=10,
            pady=10
        )


        tk.Label(
            i_form,
            text="Truck:",
            bg="white"
        ).grid(
            row=0,
            column=0,
            padx=5
        )

        i_truck = tk.Entry(
            i_form,
            width=18
        )

        i_truck.grid(
            row=0,
            column=1,
            padx=5
        )


        tk.Label(
            i_form,
            text="Bag:",
            bg="white"
        ).grid(
            row=0,
            column=2,
            padx=5
        )

        i_bag = tk.Entry(
            i_form,
            width=10
        )

        i_bag.grid(
            row=0,
            column=3,
            padx=5
        )


        tk.Label(
            i_form,
            text="Brand:",
            bg="white"
        ).grid(
            row=0,
            column=4,
            padx=5
        )

        i_brand = ttk.Combobox(
            i_form,
            values=PRODUCTS,
            width=12,
            state="readonly"
        )

        i_brand.set(
            "PPC"
        )

        i_brand.grid(
            row=0,
            column=5,
            padx=5
        )


        tk.Label(
            i_form,
            text="RoadLine:",
            bg="white"
        ).grid(
            row=0,
            column=6,
            padx=5
        )

        i_road = tk.Entry(
            i_form,
            width=18
        )

        i_road.grid(
            row=0,
            column=7,
            padx=5
        )


        i_cols = (
            "ID",
            "Truck",
            "Bag",
            "Brand",
            "RoadLine"
        )

        i_tree = ttk.Treeview(
            tab_inward,
            columns=i_cols,
            show="headings",
            height=14
        )

        for c in i_cols:

            i_tree.heading(
                c,
                text=c
            )

        i_tree.column(
            "ID",
            width=55,
            anchor="center"
        )

        i_tree.column(
            "Truck",
            width=220
        )

        i_tree.column(
            "Bag",
            width=100,
            anchor="center"
        )

        i_tree.column(
            "Brand",
            width=150,
            anchor="center"
        )

        i_tree.column(
            "RoadLine",
            width=250
        )


        i_scroll = ttk.Scrollbar(
            tab_inward,
            orient="vertical",
            command=i_tree.yview
        )

        i_tree.configure(
            yscrollcommand=i_scroll.set
        )

        i_tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(10, 0),
            pady=5
        )

        i_scroll.pack(
            side="right",
            fill="y",
            padx=(0, 10),
            pady=5
        )


        # ====================================================
        # SUMMARY TAB
        # ====================================================

        op_note = (
            "BRAND STOCK SUMMARY - ADMIN EDIT OP-ST"
            if is_admin
            else "BRAND STOCK SUMMARY - OP-ST LOCKED"
        )

        box = tk.LabelFrame(
            tab_summary,
            text=op_note,
            padx=15,
            pady=15,
            bg="white",
            font=("Arial", 10, "bold")
        )

        box.pack(
            fill="x",
            padx=15,
            pady=15
        )


        headers = [
            "Brand",
            "OP-ST",
            "In",
            "Out",
            "Total"
        ]

        for idx, h in enumerate(headers):

            tk.Label(
                box,
                text=h,
                bg="#e3f2fd",
                font=("Arial", 10, "bold"),
                width=16,
                relief="ridge",
                pady=5
            ).grid(
                row=0,
                column=idx,
                padx=2,
                pady=2
            )


        op_state = (
            "normal"
            if is_admin
            else "disabled"
        )


        # PPC

        tk.Label(
            box,
            text="Wonder PPC",
            bg="white",
            width=16
        ).grid(
            row=1,
            column=0,
            padx=2,
            pady=5
        )

        ppc_op = tk.Entry(
            box,
            width=16,
            state=op_state,
            justify="center"
        )

        ppc_op.insert(
            0,
            "0"
        )

        ppc_op.grid(
            row=1,
            column=1,
            padx=2
        )

        ppc_in_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        ppc_in_lbl.grid(
            row=1,
            column=2
        )

        ppc_out_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        ppc_out_lbl.grid(
            row=1,
            column=3
        )

        ppc_tot_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#e8f5e9",
            font=("Arial", 10, "bold")
        )

        ppc_tot_lbl.grid(
            row=1,
            column=4
        )


        # PLUS

        tk.Label(
            box,
            text="Wonder PLUS",
            bg="white",
            width=16
        ).grid(
            row=2,
            column=0,
            padx=2,
            pady=5
        )

        plus_op = tk.Entry(
            box,
            width=16,
            state=op_state,
            justify="center"
        )

        plus_op.insert(
            0,
            "0"
        )

        plus_op.grid(
            row=2,
            column=1
        )

        plus_in_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        plus_in_lbl.grid(
            row=2,
            column=2
        )

        plus_out_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        plus_out_lbl.grid(
            row=2,
            column=3
        )

        plus_tot_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#e8f5e9",
            font=("Arial", 10, "bold")
        )

        plus_tot_lbl.grid(
            row=2,
            column=4
        )


        # XTREME

        tk.Label(
            box,
            text="Wonder Xtreme",
            bg="white",
            width=16
        ).grid(
            row=3,
            column=0,
            padx=2,
            pady=5
        )

        xtreme_op = tk.Entry(
            box,
            width=16,
            state=op_state,
            justify="center"
        )

        xtreme_op.insert(
            0,
            "0"
        )

        xtreme_op.grid(
            row=3,
            column=1
        )

        xtreme_in_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        xtreme_in_lbl.grid(
            row=3,
            column=2
        )

        xtreme_out_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#f5f5f5"
        )

        xtreme_out_lbl.grid(
            row=3,
            column=3
        )

        xtreme_tot_lbl = tk.Label(
            box,
            text="0",
            width=16,
            relief="sunken",
            bg="#e8f5e9",
            font=("Arial", 10, "bold")
        )

        xtreme_tot_lbl.grid(
            row=3,
            column=4
        )


        # ====================================================
        # OP VALUE HELPER
        # ====================================================

        def set_op_value(
            entry_widget,
            val
        ):

            old_state = entry_widget.cget(
                "state"
            )

            entry_widget.config(
                state="normal"
            )

            entry_widget.delete(
                0,
                "end"
            )

            entry_widget.insert(
                0,
                str(val)
            )

            entry_widget.config(
                state=old_state
            )


        # ====================================================
        # SAVE META
        # ====================================================

        def save_meta():

            d, dt = get_ctx()

            if not d or not dt:
                return False

            if not ensure_meta(
                d,
                dt
            ):
                return False

            try:

                p_op = int(
                    float(
                        ppc_op.get().strip()
                        or "0"
                    )
                )

                pl_op = int(
                    float(
                        plus_op.get().strip()
                        or "0"
                    )
                )

                x_op = int(
                    float(
                        xtreme_op.get().strip()
                        or "0"
                    )
                )

            except ValueError:

                messagebox.showwarning(
                    "Invalid OP-ST",
                    "OP-ST mein sirf number enter karein.",
                    parent=self.root
                )

                return False


            r_no = (
                report_no_entry.get().strip()
                or "84"
            )

            try:

                cur = self.conn.cursor()

                if is_admin:

                    cur.execute(
                        """
                        UPDATE report_meta
                        SET report_no = ?,
                            ppc_op = ?,
                            plus_op = ?,
                            xtreme_op = ?
                        WHERE depot = ?
                        AND report_date = ?
                        """,
                        (
                            r_no,
                            p_op,
                            pl_op,
                            x_op,
                            d,
                            dt
                        )
                    )

                else:

                    cur.execute(
                        """
                        UPDATE report_meta
                        SET report_no = ?
                        WHERE depot = ?
                        AND report_date = ?
                        """,
                        (
                            r_no,
                            d,
                            dt
                        )
                    )

                self.conn.commit()

                return True

            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Save Error",
                    f"Report data save nahi hua:\n\n{ex}",
                    parent=self.root
                )

                return False


        # ====================================================
        # COMPUTE DAY
        # ====================================================

        def compute_day(
            d,
            dt
        ):

            cur = self.conn.cursor()

            cur.execute(
                """
                SELECT
                    ppc_op,
                    plus_op,
                    xtreme_op
                FROM report_meta
                WHERE depot = ?
                AND report_date = ?
                """,
                (
                    d,
                    dt
                )
            )

            meta = cur.fetchone()

            if meta:

                p_op = meta[0] or 0
                pl_op = meta[1] or 0
                x_op = meta[2] or 0

            else:

                p_op = 0
                pl_op = 0
                x_op = 0


            cur.execute(
                """
                SELECT bag, brand
                FROM inward_entries
                WHERE depot = ?
                AND report_date = ?
                """,
                (
                    d,
                    dt
                )
            )

            in_rows = cur.fetchall()


            cur.execute(
                """
                SELECT bag, brand
                FROM dispatch_entries
                WHERE depot = ?
                AND report_date = ?
                """,
                (
                    d,
                    dt
                )
            )

            out_rows = cur.fetchall()


            p_in = sum(
                int(r[0] or 0)
                for r in in_rows
                if str(r[1]).strip().upper() == "PPC"
            )

            pl_in = sum(
                int(r[0] or 0)
                for r in in_rows
                if str(r[1]).strip().upper() == "PLUS"
            )

            x_in = sum(
                int(r[0] or 0)
                for r in in_rows
                if str(r[1]).strip().upper() == "XTREME"
            )


            p_out = sum(
                int(r[0] or 0)
                for r in out_rows
                if str(r[1]).strip().upper() == "PPC"
            )

            pl_out = sum(
                int(r[0] or 0)
                for r in out_rows
                if str(r[1]).strip().upper() == "PLUS"
            )

            x_out = sum(
                int(r[0] or 0)
                for r in out_rows
                if str(r[1]).strip().upper() == "XTREME"
            )


            return (
                (
                    p_op,
                    p_in,
                    p_out,
                    p_op + p_in - p_out
                ),
                (
                    pl_op,
                    pl_in,
                    pl_out,
                    pl_op + pl_in - pl_out
                ),
                (
                    x_op,
                    x_in,
                    x_out,
                    x_op + x_in - x_out
                )
            )


        # ====================================================
        # REFRESH SUMMARY
        # ====================================================

        def refresh_summary(
            show_message=False
        ):

            d, dt = get_ctx()

            if not d or not dt:
                return

            if is_admin:

                if not save_meta():
                    return

            else:

                ensure_meta(
                    d,
                    dt
                )


            values = compute_day(
                d,
                dt
            )

            (
                p_op,
                p_in,
                p_out,
                p_tot
            ), (
                pl_op,
                pl_in,
                pl_out,
                pl_tot
            ), (
                x_op,
                x_in,
                x_out,
                x_tot
            ) = values


            ppc_in_lbl.config(
                text=str(p_in)
            )

            ppc_out_lbl.config(
                text=str(p_out)
            )

            ppc_tot_lbl.config(
                text=str(p_tot)
            )


            plus_in_lbl.config(
                text=str(pl_in)
            )

            plus_out_lbl.config(
                text=str(pl_out)
            )

            plus_tot_lbl.config(
                text=str(pl_tot)
            )


            xtreme_in_lbl.config(
                text=str(x_in)
            )

            xtreme_out_lbl.config(
                text=str(x_out)
            )

            xtreme_tot_lbl.config(
                text=str(x_tot)
            )


            if show_message:

                messagebox.showinfo(
                    "Updated",
                    "Stock Summary successfully update ho gaya.",
                    parent=self.root
                )


        # ====================================================
        # LOAD DATA
        # ====================================================

        def load_data(event=None):

            try:

                d, dt = get_ctx()

                if not d or not dt:
                    return


                cur = self.conn.cursor()


                # REPORT META

                cur.execute(
                    """
                    SELECT
                        report_no,
                        ppc_op,
                        plus_op,
                        xtreme_op
                    FROM report_meta
                    WHERE depot = ?
                    AND report_date = ?
                    """,
                    (
                        d,
                        dt
                    )
                )

                meta = cur.fetchone()


                if meta:

                    report_no_entry.delete(
                        0,
                        "end"
                    )

                    report_no_entry.insert(
                        0,
                        str(
                            meta[0]
                            or "84"
                        )
                    )

                    set_op_value(
                        ppc_op,
                        meta[1] or 0
                    )

                    set_op_value(
                        plus_op,
                        meta[2] or 0
                    )

                    set_op_value(
                        xtreme_op,
                        meta[3] or 0
                    )

                else:

                    set_op_value(
                        ppc_op,
                        0
                    )

                    set_op_value(
                        plus_op,
                        0
                    )

                    set_op_value(
                        xtreme_op,
                        0
                    )


                # CLEAR DISPATCH TREE

                for item in d_tree.get_children():

                    d_tree.delete(
                        item
                    )


                cur.execute(
                    """
                    SELECT
                        id,
                        party,
                        bag,
                        brand,
                        truck
                    FROM dispatch_entries
                    WHERE depot = ?
                    AND report_date = ?
                    ORDER BY id ASC
                    """,
                    (
                        d,
                        dt
                    )
                )

                rows = cur.fetchall()


                for r in rows:

                    d_tree.insert(
                        "",
                        "end",
                        values=r
                    )


                # CLEAR INWARD TREE

                for item in i_tree.get_children():

                    i_tree.delete(
                        item
                    )


                cur.execute(
                    """
                    SELECT
                        id,
                        truck,
                        bag,
                        brand,
                        roadline
                    FROM inward_entries
                    WHERE depot = ?
                    AND report_date = ?
                    ORDER BY id ASC
                    """,
                    (
                        d,
                        dt
                    )
                )

                rows = cur.fetchall()


                for r in rows:

                    i_tree.insert(
                        "",
                        "end",
                        values=r
                    )


                # SUMMARY

                refresh_summary()


                status_lbl.config(
                    text=(
                        f"User: {user_id}  |  "
                        f"Depot: {d}  |  "
                        f"Date: {dt}  |  "
                        f"Dispatch: {len(d_tree.get_children())}  |  "
                        f"Inward: {len(i_tree.get_children())}"
                    )
                )


            except Exception as ex:

                messagebox.showerror(
                    "Load Error",
                    f"Data load nahi hua:\n\n{ex}",
                    parent=self.root
                )

                print(
                    traceback.format_exc()
                )


        # ====================================================
        # ADD DISPATCH
        # ====================================================

        def add_dispatch():

            try:

                d, dt = get_ctx()

                party = d_party.get().strip()
                bag_s = d_bag.get().strip()
                brand = d_brand.get().strip()
                truck = d_truck.get().strip()


                if not d or not dt:

                    messagebox.showwarning(
                        "Missing",
                        "Depot aur Date select karein.",
                        parent=self.root
                    )

                    return


                if not party:

                    messagebox.showwarning(
                        "Missing",
                        "Party name enter karein.",
                        parent=self.root
                    )

                    d_party.focus_set()

                    return


                if not bag_s:

                    messagebox.showwarning(
                        "Missing",
                        "Bag quantity enter karein.",
                        parent=self.root
                    )

                    d_bag.focus_set()

                    return


                if not brand:

                    messagebox.showwarning(
                        "Missing",
                        "Brand select karein.",
                        parent=self.root
                    )

                    return


                try:

                    bag = int(
                        float(bag_s)
                    )

                    if bag <= 0:
                        raise ValueError

                except ValueError:

                    messagebox.showerror(
                        "Invalid Bag",
                        "Bag mein 0 se bada valid number enter karein.",
                        parent=self.root
                    )

                    d_bag.focus_set()

                    return


                # ENSURE META

                if not ensure_meta(
                    d,
                    dt
                ):
                    return


                cur = self.conn.cursor()


                cur.execute(
                    """
                    INSERT INTO dispatch_entries
                    (
                        depot,
                        report_date,
                        party,
                        bag,
                        brand,
                        truck
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d,
                        dt,
                        party,
                        bag,
                        brand,
                        truck
                    )
                )


                new_id = cur.lastrowid


                self.conn.commit()


                # ADD DIRECTLY TO SCREEN

                d_tree.insert(
                    "",
                    "end",
                    values=(
                        new_id,
                        party,
                        bag,
                        brand,
                        truck
                    )
                )


                # CLEAR INPUT

                d_party.delete(
                    0,
                    "end"
                )

                d_bag.delete(
                    0,
                    "end"
                )

                d_truck.delete(
                    0,
                    "end"
                )


                # UPDATE SUMMARY

                refresh_summary()


                # STATUS

                status_lbl.config(
                    text=(
                        f"User: {user_id} | "
                        f"Depot: {d} | "
                        f"Date: {dt} | "
                        f"Dispatch Added: {party} - {bag} Bags"
                    )
                )


                # NEXT ENTRY

                d_party.focus_set()


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Dispatch Add Error",
                    (
                        "Dispatch entry add nahi hui.\n\n"
                        f"Error:\n{ex}"
                    ),
                    parent=self.root
                )

                print(
                    traceback.format_exc()
                )


        # ====================================================
        # DELETE DISPATCH
        # ====================================================

        def del_dispatch():

            selected = d_tree.selection()

            if not selected:

                messagebox.showwarning(
                    "Select Row",
                    "Delete karne ke liye pehle row select karein.",
                    parent=self.root
                )

                return


            if not messagebox.askyesno(
                "Confirm Delete",
                f"{len(selected)} dispatch row delete karein?",
                parent=self.root
            ):
                return


            try:

                cur = self.conn.cursor()

                for item in selected:

                    vals = d_tree.item(
                        item,
                        "values"
                    )

                    if vals:

                        cur.execute(
                            """
                            DELETE FROM dispatch_entries
                            WHERE id = ?
                            """,
                            (
                                vals[0],
                            )
                        )


                self.conn.commit()


                for item in selected:

                    d_tree.delete(
                        item
                    )


                refresh_summary()


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Delete Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # ADD INWARD
        # ====================================================

        def add_inward():

            try:

                d, dt = get_ctx()

                truck = i_truck.get().strip()
                bag_s = i_bag.get().strip()
                brand = i_brand.get().strip()
                road = i_road.get().strip()


                if not d or not dt:

                    messagebox.showwarning(
                        "Missing",
                        "Depot aur Date select karein.",
                        parent=self.root
                    )

                    return


                if not truck:

                    messagebox.showwarning(
                        "Missing",
                        "Truck number enter karein.",
                        parent=self.root
                    )

                    i_truck.focus_set()

                    return


                if not bag_s:

                    messagebox.showwarning(
                        "Missing",
                        "Bag quantity enter karein.",
                        parent=self.root
                    )

                    i_bag.focus_set()

                    return


                if not brand:

                    messagebox.showwarning(
                        "Missing",
                        "Brand select karein.",
                        parent=self.root
                    )

                    return


                try:

                    bag = int(
                        float(bag_s)
                    )

                    if bag <= 0:
                        raise ValueError

                except ValueError:

                    messagebox.showerror(
                        "Invalid Bag",
                        "Bag mein 0 se bada valid number enter karein.",
                        parent=self.root
                    )

                    i_bag.focus_set()

                    return


                if not ensure_meta(
                    d,
                    dt
                ):
                    return


                cur = self.conn.cursor()


                cur.execute(
                    """
                    INSERT INTO inward_entries
                    (
                        depot,
                        report_date,
                        truck,
                        bag,
                        brand,
                        roadline
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d,
                        dt,
                        truck,
                        bag,
                        brand,
                        road
                    )
                )


                new_id = cur.lastrowid


                self.conn.commit()


                i_tree.insert(
                    "",
                    "end",
                    values=(
                        new_id,
                        truck,
                        bag,
                        brand,
                        road
                    )
                )


                i_truck.delete(
                    0,
                    "end"
                )

                i_bag.delete(
                    0,
                    "end"
                )

                i_road.delete(
                    0,
                    "end"
                )


                refresh_summary()


                status_lbl.config(
                    text=(
                        f"User: {user_id} | "
                        f"Depot: {d} | "
                        f"Date: {dt} | "
                        f"Inward Added: {truck} - {bag} Bags"
                    )
                )


                i_truck.focus_set()


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Inward Add Error",
                    (
                        "Inward entry add nahi hui.\n\n"
                        f"Error:\n{ex}"
                    ),
                    parent=self.root
                )

                print(
                    traceback.format_exc()
                )


        # ====================================================
        # DELETE INWARD
        # ====================================================

        def del_inward():

            selected = i_tree.selection()

            if not selected:

                messagebox.showwarning(
                    "Select Row",
                    "Delete karne ke liye pehle row select karein.",
                    parent=self.root
                )

                return


            if not messagebox.askyesno(
                "Confirm Delete",
                f"{len(selected)} inward row delete karein?",
                parent=self.root
            ):
                return


            try:

                cur = self.conn.cursor()

                for item in selected:

                    vals = i_tree.item(
                        item,
                        "values"
                    )

                    if vals:

                        cur.execute(
                            """
                            DELETE FROM inward_entries
                            WHERE id = ?
                            """,
                            (
                                vals[0],
                            )
                        )


                self.conn.commit()


                for item in selected:

                    i_tree.delete(
                        item
                    )


                refresh_summary()


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Delete Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # LOAD PREVIOUS CLOSING
        # ====================================================

        def load_prev_closing():

            if not is_admin:

                messagebox.showwarning(
                    "Access Denied",
                    "OP-ST load karne ka अधिकार sirf Admin ko hai.",
                    parent=self.root
                )

                return


            d, dt = get_ctx()


            try:

                current_date = datetime.strptime(
                    dt,
                    "%Y-%m-%d"
                ).date()

                prev_dt = str(
                    current_date
                    - timedelta(days=1)
                )

            except ValueError:

                messagebox.showerror(
                    "Invalid Date",
                    "Date YYYY-MM-DD format mein likhein.",
                    parent=self.root
                )

                return


            try:

                previous = compute_day(
                    d,
                    prev_dt
                )

                (
                    _,
                    _,
                    _,
                    prev_p_tot
                ), (
                    _,
                    _,
                    _,
                    prev_pl_tot
                ), (
                    _,
                    _,
                    _,
                    prev_x_tot
                ) = previous


                set_op_value(
                    ppc_op,
                    prev_p_tot
                )

                set_op_value(
                    plus_op,
                    prev_pl_tot
                )

                set_op_value(
                    xtreme_op,
                    prev_x_tot
                )


                refresh_summary()


                messagebox.showinfo(
                    "Loaded",
                    (
                        f"{prev_dt} ka closing stock "
                        "OP-ST mein load ho gaya."
                    ),
                    parent=self.root
                )


            except Exception as ex:

                messagebox.showerror(
                    "Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # CLEAR DAY
        # ====================================================

        def clear_day():

            d, dt = get_ctx()


            if not messagebox.askyesno(
                "Confirm Delete",
                (
                    f"Depot: {d}\n"
                    f"Date: {dt}\n\n"
                    "Is date ka Dispatch, Inward aur "
                    "OP-ST data delete karein?"
                ),
                parent=self.root
            ):
                return


            try:

                cur = self.conn.cursor()


                cur.execute(
                    """
                    DELETE FROM dispatch_entries
                    WHERE depot = ?
                    AND report_date = ?
                    """,
                    (
                        d,
                        dt
                    )
                )


                cur.execute(
                    """
                    DELETE FROM inward_entries
                    WHERE depot = ?
                    AND report_date = ?
                    """,
                    (
                        d,
                        dt
                    )
                )


                cur.execute(
                    """
                    DELETE FROM report_meta
                    WHERE depot = ?
                    AND report_date = ?
                    """,
                    (
                        d,
                        dt
                    )
                )


                self.conn.commit()


                load_data()


                messagebox.showinfo(
                    "Deleted",
                    "Current date ka complete data delete ho gaya.",
                    parent=self.root
                )


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Delete Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # FETCH REPORT SNAPSHOT
        # ====================================================

        def fetch_report_snapshot(
            d,
            dt
        ):

            cur = self.conn.cursor()


            cur.execute(
                """
                SELECT
                    party,
                    bag,
                    brand,
                    truck
                FROM dispatch_entries
                WHERE depot = ?
                AND report_date = ?
                ORDER BY id ASC
                """,
                (
                    d,
                    dt
                )
            )

            d_rows = cur.fetchall()


            cur.execute(
                """
                SELECT
                    truck,
                    bag,
                    brand,
                    roadline
                FROM inward_entries
                WHERE depot = ?
                AND report_date = ?
                ORDER BY id ASC
                """,
                (
                    d,
                    dt
                )
            )

            i_rows = cur.fetchall()


            summary = compute_day(
                d,
                dt
            )


            return (
                d_rows,
                i_rows,
                summary
            )


        # ====================================================
        # EXPORT EXCEL
        # ====================================================

        def export_excel():

            try:

                d, dt = get_ctx()

                save_meta()

                r_no = (
                    report_no_entry.get().strip()
                    or "84"
                )


                default_name = (
                    f"Depot_Report_{d}_"
                    f"No{r_no}_{dt}.xlsx"
                    .replace(" ", "_")
                )


                file_path = filedialog.asksaveasfilename(
                    parent=self.root,
                    title="Save Excel Report",
                    defaultextension=".xlsx",
                    initialfile=default_name,
                    filetypes=[
                        (
                            "Excel Files",
                            "*.xlsx"
                        )
                    ]
                )


                if not file_path:
                    return


                (
                    d_rows,
                    i_rows,
                    summary
                ) = fetch_report_snapshot(
                    d,
                    dt
                )


                (
                    p_op,
                    p_in,
                    p_out,
                    p_tot
                ), (
                    pl_op,
                    pl_in,
                    pl_out,
                    pl_tot
                ), (
                    x_op,
                    x_in,
                    x_out,
                    x_tot
                ) = summary


                wb = Workbook()

                ws = wb.active

                ws.title = "Daily Report"


                ws.append(
                    [
                        "Depot",
                        d,
                        "",
                        "Report No",
                        r_no,
                        "Date",
                        dt
                    ]
                )

                ws.append([])


                ws.append(
                    [
                        "DISPATCH (OUT)"
                    ]
                )

                ws.append(
                    [
                        "Party",
                        "Bag",
                        "Brand",
                        "Truck"
                    ]
                )


                for row in d_rows:

                    ws.append(
                        list(row)
                    )


                ws.append([])


                ws.append(
                    [
                        "INWARD TRUCKS (IN)"
                    ]
                )

                ws.append(
                    [
                        "Truck",
                        "Bag",
                        "Brand",
                        "RoadLine"
                    ]
                )


                for row in i_rows:

                    ws.append(
                        list(row)
                    )


                ws.append([])


                ws.append(
                    [
                        "BRAND STOCK SUMMARY"
                    ]
                )

                ws.append(
                    [
                        "Brand",
                        "OP-ST",
                        "In",
                        "Out",
                        "Total"
                    ]
                )


                ws.append(
                    [
                        "Wonder PPC",
                        p_op,
                        p_in,
                        p_out,
                        p_tot
                    ]
                )

                ws.append(
                    [
                        "Wonder PLUS",
                        pl_op,
                        pl_in,
                        pl_out,
                        pl_tot
                    ]
                )

                ws.append(
                    [
                        "Wonder Xtreme",
                        x_op,
                        x_in,
                        x_out,
                        x_tot
                    ]
                )


                ws.append(
                    [
                        "Grand Total",
                        p_op + pl_op + x_op,
                        p_in + pl_in + x_in,
                        p_out + pl_out + x_out,
                        p_tot + pl_tot + x_tot
                    ]
                )


                # Column widths

                widths = {
                    "A": 25,
                    "B": 14,
                    "C": 16,
                    "D": 22,
                    "E": 14,
                    "F": 14,
                    "G": 16,
                }


                for col, width in widths.items():

                    ws.column_dimensions[
                        col
                    ].width = width


                wb.save(
                    file_path
                )


                messagebox.showinfo(
                    "Excel Saved",
                    (
                        "Excel report successfully save ho gaya.\n\n"
                        f"{file_path}"
                    ),
                    parent=self.root
                )


            except Exception as ex:

                messagebox.showerror(
                    "Excel Export Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # EXPORT JPG
        # ====================================================

        def export_jpg():

            try:

                d, dt = get_ctx()

                save_meta()

                r_no = (
                    report_no_entry.get().strip()
                    or "84"
                )


                default_name = (
                    f"Depot_Report_{d}_"
                    f"No{r_no}_{dt}.jpg"
                    .replace(" ", "_")
                )


                file_path = filedialog.asksaveasfilename(
                    parent=self.root,
                    title="Save JPG Report",
                    defaultextension=".jpg",
                    initialfile=default_name,
                    filetypes=[
                        (
                            "JPEG Image",
                            "*.jpg"
                        )
                    ]
                )


                if not file_path:
                    return


                (
                    d_rows,
                    i_rows,
                    summary
                ) = fetch_report_snapshot(
                    d,
                    dt
                )


                (
                    p_op,
                    p_in,
                    p_out,
                    p_tot
                ), (
                    pl_op,
                    pl_in,
                    pl_out,
                    pl_tot
                ), (
                    x_op,
                    x_in,
                    x_out,
                    x_tot
                ) = summary


                title_font, sec_font, body_font, small_font = get_fonts()


                width = 1200
                margin = 35
                row_h = 32
                header_h = 38


                d_count = max(
                    1,
                    len(d_rows)
                )

                i_count = max(
                    1,
                    len(i_rows)
                )


                est_height = (
                    150
                    + 60
                    + header_h
                    + d_count * row_h
                    + 35
                    + 60
                    + header_h
                    + i_count * row_h
                    + 35
                    + 60
                    + header_h
                    + 4 * row_h
                    + 60
                )


                img = Image.new(
                    "RGB",
                    (
                        width,
                        est_height
                    ),
                    "#f4f6f9"
                )


                draw = ImageDraw.Draw(
                    img
                )


                # Banner

                draw.rectangle(
                    [
                        margin,
                        margin,
                        width - margin,
                        margin + 80
                    ],
                    fill="#0d47a1"
                )


                draw.text(
                    (
                        margin + 20,
                        margin + 12
                    ),
                    (
                        f"DAILY DEPOT REPORT | "
                        f"DEPOT: {d}"
                    ),
                    fill="white",
                    font=title_font
                )


                draw.text(
                    (
                        margin + 20,
                        margin + 48
                    ),
                    (
                        f"Report No: {r_no}    "
                        f"|    Date: {dt}"
                    ),
                    fill="#e3f2fd",
                    font=small_font
                )


                y = margin + 105


                def draw_table(
                    title,
                    section_color,
                    headers,
                    widths,
                    rows,
                    highlight_last=False
                ):

                    nonlocal y


                    draw.text(
                        (
                            margin,
                            y
                        ),
                        title,
                        fill=section_color,
                        font=sec_font
                    )


                    y += 32


                    x = margin


                    for h, w in zip(
                        headers,
                        widths
                    ):

                        draw.rectangle(
                            [
                                x,
                                y,
                                x + w,
                                y + header_h
                            ],
                            fill=section_color
                        )


                        draw.text(
                            (
                                x + 10,
                                y + 9
                            ),
                            str(h),
                            fill="white",
                            font=body_font
                        )


                        x += w


                    y += header_h


                    if rows:

                        display_rows = rows

                    else:

                        display_rows = [
                            [
                                "No entries recorded"
                            ]
                            + [
                                ""
                            ] * (
                                len(headers) - 1
                            )
                        ]


                    for idx, row in enumerate(
                        display_rows
                    ):

                        is_last = (
                            highlight_last
                            and
                            idx == len(display_rows) - 1
                        )


                        bg = (
                            "#e8f5e9"
                            if is_last
                            else (
                                "#ffffff"
                                if idx % 2 == 0
                                else "#f0f4f8"
                            )
                        )


                        txt = (
                            "#1b5e20"
                            if is_last
                            else "#1e293b"
                        )


                        x = margin


                        for value, w in zip(
                            row,
                            widths
                        ):

                            draw.rectangle(
                                [
                                    x,
                                    y,
                                    x + w,
                                    y + row_h
                                ],
                                fill=bg,
                                outline="#cbd5e1"
                            )


                            draw.text(
                                (
                                    x + 10,
                                    y + 8
                                ),
                                str(
                                    value
                                    if value is not None
                                    else ""
                                ),
                                fill=txt,
                                font=(
                                    sec_font
                                    if is_last
                                    else body_font
                                )
                            )


                            x += w


                        y += row_h


                    y += 22


                draw_table(
                    "1. DISPATCH (OUTWARD)",
                    "#1b5e20",
                    [
                        "Party",
                        "Bag",
                        "Brand",
                        "Truck"
                    ],
                    [
                        400,
                        130,
                        180,
                        420
                    ],
                    [
                        list(r)
                        for r in d_rows
                    ]
                )


                draw_table(
                    "2. INWARD TRUCKS (INWARD)",
                    "#01579b",
                    [
                        "Truck",
                        "Bag",
                        "Brand",
                        "RoadLine"
                    ],
                    [
                        280,
                        130,
                        180,
                        540
                    ],
                    [
                        list(r)
                        for r in i_rows
                    ]
                )


                summary_rows = [
                    [
                        "Wonder PPC",
                        p_op,
                        p_in,
                        p_out,
                        p_tot
                    ],
                    [
                        "Wonder PLUS",
                        pl_op,
                        pl_in,
                        pl_out,
                        pl_tot
                    ],
                    [
                        "Wonder Xtreme",
                        x_op,
                        x_in,
                        x_out,
                        x_tot
                    ],
                    [
                        "Grand Total",
                        p_op + pl_op + x_op,
                        p_in + pl_in + x_in,
                        p_out + pl_out + x_out,
                        p_tot + pl_tot + x_tot
                    ]
                ]


                draw_table(
                    "3. BRAND STOCK SUMMARY",
                    "#4a148c",
                    [
                        "Brand",
                        "OP-ST",
                        "In",
                        "Out",
                        "Total"
                    ],
                    [
                        390,
                        170,
                        170,
                        170,
                        230
                    ],
                    summary_rows,
                    highlight_last=True
                )


                draw.text(
                    (
                        margin,
                        y
                    ),
                    (
                        "Generated on "
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} "
                        "| Depot Report System"
                    ),
                    fill="#64748b",
                    font=small_font
                )


                final_img = img.crop(
                    (
                        0,
                        0,
                        width,
                        min(
                            est_height,
                            y + 40
                        )
                    )
                )


                final_img.save(
                    file_path,
                    format="JPEG",
                    quality=95
                )


                messagebox.showinfo(
                    "JPG Saved",
                    (
                        "JPG report successfully save ho gaya.\n\n"
                        f"{file_path}"
                    ),
                    parent=self.root
                )


            except Exception as ex:

                messagebox.showerror(
                    "JPG Export Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # IMPORT EXCEL
        # ====================================================

        def import_from_excel():

            if not is_admin:

                messagebox.showwarning(
                    "Access Denied",
                    "Import Excel sirf Admin ke liye hai.",
                    parent=self.root
                )

                return


            file_path = filedialog.askopenfilename(
                parent=self.root,
                title="Select Depot Excel File",
                filetypes=[
                    (
                        "Excel Files",
                        "*.xlsx"
                    )
                ]
            )


            if not file_path:
                return


            try:

                wb = load_workbook(
                    file_path,
                    data_only=True
                )

                ws = wb.active

                rows = list(
                    ws.iter_rows(
                        values_only=True
                    )
                )


            except Exception as ex:

                messagebox.showerror(
                    "Import Error",
                    str(ex),
                    parent=self.root
                )

                return


            cur_d, cur_dt = get_ctx()

            imp_depot = cur_d
            imp_date = cur_dt

            imp_rno = (
                report_no_entry.get().strip()
                or "84"
            )

            imp_ppc_op = None
            imp_plus_op = None
            imp_xtreme_op = None

            section = None

            d_imported = 0
            i_imported = 0


            try:

                cur = self.conn.cursor()


                for r in rows:

                    vals = [
                        ""
                        if v is None
                        else str(v).strip()
                        for v in r
                    ]


                    non_empty = [
                        v
                        for v in vals
                        if v != ""
                    ]


                    if not non_empty:
                        continue


                    first = vals[0].upper()


                    # HEADER

                    if (
                        first == "DEPOT"
                        and len(vals) >= 7
                    ):

                        if vals[1]:
                            imp_depot = vals[1]

                        if vals[4]:
                            imp_rno = vals[4]

                        if vals[6]:
                            imp_date = vals[6]

                        continue


                    # SECTION

                    if "DISPATCH" in first:

                        section = "DISPATCH"
                        continue


                    if "INWARD TRUCKS" in first:

                        section = "INWARD"
                        continue


                    if "BRAND STOCK SUMMARY" in first:

                        section = "SUMMARY"
                        continue


                    # DISPATCH

                    if section == "DISPATCH":

                        if first == "PARTY":
                            continue


                        party = (
                            vals[0]
                            if len(vals) > 0
                            else ""
                        )

                        bag_s = (
                            vals[1]
                            if len(vals) > 1
                            else ""
                        )

                        brand = (
                            vals[2]
                            if len(vals) > 2
                            else "PPC"
                        )

                        truck = (
                            vals[3]
                            if len(vals) > 3
                            else ""
                        )


                        if party and bag_s:

                            try:

                                bag = int(
                                    float(bag_s)
                                )


                                cur.execute(
                                    """
                                    INSERT INTO dispatch_entries
                                    (
                                        depot,
                                        report_date,
                                        party,
                                        bag,
                                        brand,
                                        truck
                                    )
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        imp_depot,
                                        imp_date,
                                        party,
                                        bag,
                                        brand or "PPC",
                                        truck
                                    )
                                )


                                d_imported += 1


                            except ValueError:
                                pass


                    # INWARD

                    elif section == "INWARD":

                        if first == "TRUCK":
                            continue


                        truck = (
                            vals[0]
                            if len(vals) > 0
                            else ""
                        )

                        bag_s = (
                            vals[1]
                            if len(vals) > 1
                            else ""
                        )

                        brand = (
                            vals[2]
                            if len(vals) > 2
                            else "PPC"
                        )

                        road = (
                            vals[3]
                            if len(vals) > 3
                            else ""
                        )


                        if truck and bag_s:

                            try:

                                bag = int(
                                    float(bag_s)
                                )


                                cur.execute(
                                    """
                                    INSERT INTO inward_entries
                                    (
                                        depot,
                                        report_date,
                                        truck,
                                        bag,
                                        brand,
                                        roadline
                                    )
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        imp_depot,
                                        imp_date,
                                        truck,
                                        bag,
                                        brand or "PPC",
                                        road
                                    )
                                )


                                i_imported += 1


                            except ValueError:
                                pass


                    # SUMMARY

                    elif section == "SUMMARY":

                        if (
                            first == "BRAND"
                            or "GRAND TOTAL" in first
                        ):
                            continue


                        if (
                            "PPC" in first
                            and len(vals) > 1
                            and vals[1]
                        ):

                            try:
                                imp_ppc_op = int(
                                    float(vals[1])
                                )
                            except ValueError:
                                pass


                        elif (
                            "PLUS" in first
                            and len(vals) > 1
                            and vals[1]
                        ):

                            try:
                                imp_plus_op = int(
                                    float(vals[1])
                                )
                            except ValueError:
                                pass


                        elif (
                            "XTREME" in first
                            and len(vals) > 1
                            and vals[1]
                        ):

                            try:
                                imp_xtreme_op = int(
                                    float(vals[1])
                                )
                            except ValueError:
                                pass


                # META

                cur.execute(
                    """
                    INSERT OR IGNORE INTO report_meta
                    (
                        depot,
                        report_date,
                        report_no,
                        ppc_op,
                        plus_op,
                        xtreme_op
                    )
                    VALUES (?, ?, ?, 0, 0, 0)
                    """,
                    (
                        imp_depot,
                        imp_date,
                        imp_rno
                    )
                )


                cur.execute(
                    """
                    UPDATE report_meta
                    SET
                        report_no = ?,
                        ppc_op = COALESCE(?, ppc_op),
                        plus_op = COALESCE(?, plus_op),
                        xtreme_op = COALESCE(?, xtreme_op)
                    WHERE depot = ?
                    AND report_date = ?
                    """,
                    (
                        imp_rno,
                        imp_ppc_op,
                        imp_plus_op,
                        imp_xtreme_op,
                        imp_depot,
                        imp_date
                    )
                )


                self.conn.commit()


                if imp_depot in DEPOTS:

                    depot_var.set(
                        imp_depot
                    )


                date_entry.delete(
                    0,
                    "end"
                )

                date_entry.insert(
                    0,
                    imp_date
                )


                report_no_entry.delete(
                    0,
                    "end"
                )

                report_no_entry.insert(
                    0,
                    imp_rno
                )


                load_data()


                messagebox.showinfo(
                    "Import Complete",
                    (
                        f"Excel import complete.\n\n"
                        f"Depot: {imp_depot}\n"
                        f"Date: {imp_date}\n"
                        f"Dispatch Rows: {d_imported}\n"
                        f"Inward Rows: {i_imported}"
                    ),
                    parent=self.root
                )


            except Exception as ex:

                try:
                    self.conn.rollback()
                except Exception:
                    pass

                messagebox.showerror(
                    "Import Error",
                    str(ex),
                    parent=self.root
                )


        # ====================================================
        # BUTTONS
        # ====================================================

        tk.Button(
            d_form,
            text="ADD DISPATCH",
            command=add_dispatch,
            bg="#2e7d32",
            fg="white",
            activebackground="#1b5e20",
            activeforeground="white",
            font=("Arial", 9, "bold"),
            width=14,
            pady=4,
            cursor="hand2"
        ).grid(
            row=0,
            column=8,
            padx=8
        )


        tk.Button(
            d_form,
            text="DELETE",
            command=del_dispatch,
            bg="#c62828",
            fg="white",
            activebackground="#8e0000",
            activeforeground="white",
            font=("Arial", 9, "bold"),
            width=10,
            pady=4,
            cursor="hand2"
        ).grid(
            row=0,
            column=9,
            padx=3
        )


        tk.Button(
            i_form,
            text="ADD INWARD",
            command=add_inward,
            bg="#2e7d32",
            fg="white",
            activebackground="#1b5e20",
            activeforeground="white",
            font=("Arial", 9, "bold"),
            width=14,
            pady=4,
            cursor="hand2"
        ).grid(
            row=0,
            column=8,
            padx=8
        )


        tk.Button(
            i_form,
            text="DELETE",
            command=del_inward,
            bg="#c62828",
            fg="white",
            activebackground="#8e0000",
            activeforeground="white",
            font=("Arial", 9, "bold"),
            width=10,
            pady=4,
            cursor="hand2"
        ).grid(
            row=0,
            column=9,
            padx=3
        )


        # ====================================================
        # TOP BUTTONS
        # ====================================================

        tk.Button(
            top_frame,
            text="LOAD DATA",
            command=load_data,
            bg="#455a64",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2"
        ).grid(
            row=0,
            column=6,
            padx=4
        )


        tk.Button(
            top_frame,
            text="CLEAR DAY",
            command=clear_day,
            bg="#b71c1c",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2"
        ).grid(
            row=0,
            column=7,
            padx=4
        )


        if is_admin:

            tk.Button(
                top_frame,
                text="IMPORT EXCEL",
                command=import_from_excel,
                bg="#6a1b9a",
                fg="white",
                font=("Arial", 9, "bold"),
                cursor="hand2"
            ).grid(
                row=0,
                column=8,
                padx=4
            )


        tk.Button(
            top_frame,
            text="LOGOUT",
            command=self.show_login,
            bg="#ef6c00",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2"
        ).grid(
            row=0,
            column=9,
            padx=4
        )


        # ====================================================
        # SUMMARY BUTTONS
        # ====================================================

        btn_row = tk.Frame(
            box,
            bg="white"
        )

        btn_row.grid(
            row=4,
            column=0,
            columnspan=5,
            pady=18
        )


        if is_admin:

            tk.Button(
                btn_row,
                text="SAVE OP-ST & RECALCULATE",
                command=lambda: refresh_summary(True),
                bg="#2e7d32",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=12,
                pady=5,
                cursor="hand2"
            ).pack(
                side="left",
                padx=6
            )


            tk.Button(
                btn_row,
                text="LOAD PREVIOUS CLOSING",
                command=load_prev_closing,
                bg="#0277bd",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=12,
                pady=5,
                cursor="hand2"
            ).pack(
                side="left",
                padx=6
            )

        else:

            tk.Button(
                btn_row,
                text="REFRESH SUMMARY",
                command=refresh_summary,
                bg="#2e7d32",
                fg="white",
                font=("Arial", 9, "bold"),
                padx=15,
                pady=5,
                cursor="hand2"
            ).pack(
                side="left",
                padx=6
            )


        # ====================================================
        # EXPORT BUTTONS
        # ====================================================

        tk.Button(
            bottom_frame,
            text="Export JPG",
            command=export_jpg,
            bg="#00695c",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=6,
            cursor="hand2"
        ).pack(
            side="right",
            padx=5
        )


        tk.Button(
            bottom_frame,
            text="Export Excel",
            command=export_excel,
            bg="#1565c0",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=6,
            cursor="hand2"
        ).pack(
            side="right",
            padx=5
        )


        # ====================================================
        # KEYBOARD SHORTCUTS
        # ====================================================

        d_party.bind(
            "<Return>",
            lambda e: d_bag.focus_set()
        )

        d_bag.bind(
            "<Return>",
            lambda e: d_truck.focus_set()
        )

        d_truck.bind(
            "<Return>",
            lambda e: add_dispatch()
        )


        i_truck.bind(
            "<Return>",
            lambda e: i_bag.focus_set()
        )

        i_bag.bind(
            "<Return>",
            lambda e: i_road.focus_set()
        )

        i_road.bind(
            "<Return>",
            lambda e: add_inward()
        )


        # ====================================================
        # EVENTS
        # ====================================================

        if not assigned_depot:

            depot_combo.bind(
                "<<ComboboxSelected>>",
                load_data
            )


        date_entry.bind(
            "<Return>",
            load_data
        )


        report_no_entry.bind(
            "<FocusOut>",
            lambda e: save_meta()
        )


        if is_admin:

            ppc_op.bind(
                "<FocusOut>",
                lambda e: refresh_summary()
            )

            plus_op.bind(
                "<FocusOut>",
                lambda e: refresh_summary()
            )

            xtreme_op.bind(
                "<FocusOut>",
                lambda e: refresh_summary()
            )


        # ====================================================
        # INITIAL LOAD
        # ====================================================

        load_data()


    # ========================================================
    # CLOSE APP
    # ========================================================

    def close(self):

        try:

            if self.conn:
                self.conn.close()

        except Exception:
            pass

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        # root = tk.Tk()

        app = DepotControllerApp(
            root
        )

        root.protocol(
            "WM_DELETE_WINDOW",
            app.close
        )

        root.mainloop()


    except Exception:

        err_text = traceback.format_exc()

        print(
            err_text,
            file=sys.stderr
        )


        try:

            messagebox.showerror(
                "Startup Error",
                err_text
            )

        except Exception:
            pass


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
