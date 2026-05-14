"""
Trading 212 desktop widget.
Run: python3 src/widget.py
Drag to reposition. Click ✕ to close. Refreshes every 5 minutes.
"""

import base64
import importlib.util
import os
import sys
import threading
import tkinter as tk
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(__file__))

# ── Colours ───────────────────────────────────────────────────────────────────
BG     = "#111827"
BG2    = "#1f2937"
FG     = "#f9fafb"
MUTED  = "#6b7280"
ACCENT = "#38bdf8"
GREEN  = "#34d399"
RED    = "#f87171"
BORDER = "#374151"

WIDTH   = 290
REFRESH = 5 * 60 * 1000  # ms

FONT       = ("Helvetica Neue", 10)
FONT_SM    = ("Helvetica Neue", 8)
FONT_LG    = ("Helvetica Neue", 13, "bold")
FONT_TITLE = ("Helvetica Neue", 14, "bold")


# ── API helpers ───────────────────────────────────────────────────────────────
def _load_creds() -> tuple[str, str]:
    key_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "private", "api-key.py")
    )
    spec = importlib.util.spec_from_file_location("_wk", key_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.api.strip(), mod.secret.strip()


def _fetch_data() -> tuple[dict, list]:
    api, secret = _load_creds()
    token = base64.b64encode(f"{api}:{secret}".encode()).decode()
    sess = requests.Session()
    sess.headers["Authorization"] = f"Basic {token}"
    base = "https://live.trading212.com/api/v0"
    summary = sess.get(f"{base}/equity/account/cash", timeout=12).json()
    raw = sess.get(f"{base}/equity/portfolio", timeout=12).json()
    positions = raw if isinstance(raw, list) else raw.get("items", [])
    return summary, positions


# ── Formatting ────────────────────────────────────────────────────────────────
def _fmt(v: float, sym: str = "£") -> str:
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1_000_000:
        return f"{sign}{sym}{a/1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}{sym}{a/1_000:.1f}K"
    return f"{sign}{sym}{a:.2f}"


def _clean(ticker: str) -> str:
    return ticker.replace("_EQ", "")


# ── Widget ────────────────────────────────────────────────────────────────────
class PortfolioWidget(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)   # no title bar / chrome
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)
        self.configure(bg=BG)
        self.resizable(False, False)

        # position: top-right corner
        sw = self.winfo_screenwidth()
        x = sw - WIDTH - 24
        self.geometry(f"{WIDTH}x480+{x}+60")

        self._drag_x = self._drag_y = 0
        self._build()
        self._schedule()
        self._start_fetch()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.focus_force())

    # ── Drag ─────────────────────────────────────────────────────────────────
    def _on_press(self, e):
        self._drag_x, self._drag_y = e.x, e.y

    def _on_drag(self, e):
        x = self.winfo_x() + e.x - self._drag_x
        y = self.winfo_y() + e.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    # ── Build static skeleton ─────────────────────────────────────────────────
    def _build(self):
        root = tk.Frame(self, bg=BG, padx=16, pady=14)
        root.pack(fill=tk.BOTH, expand=True)
        for event in ("<ButtonPress-1>", "<B1-Motion>"):
            root.bind(event, self._on_press if "Press" in event else self._on_drag)

        # header
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr, text="Portfolio", bg=BG, fg=FG, font=FONT_TITLE).pack(side=tk.LEFT)

        close = tk.Label(hdr, text="✕", bg=BG, fg=MUTED, font=FONT, cursor="hand2", padx=2)
        close.pack(side=tk.RIGHT)
        close.bind("<Button-1>", lambda _: self.destroy())

        self._refresh_btn = tk.Label(hdr, text="↻", bg=BG, fg=MUTED, font=("Helvetica Neue", 14), cursor="hand2", padx=6)
        self._refresh_btn.pack(side=tk.RIGHT)
        self._refresh_btn.bind("<Button-1>", lambda _: self._start_fetch())

        tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 10))

        # KPI area (2 columns × 2 rows)
        self._kpi = tk.Frame(root, bg=BG)
        self._kpi.pack(fill=tk.X, pady=(0, 12))
        self._kpi.columnconfigure(0, weight=1)
        self._kpi.columnconfigure(1, weight=1)

        # Holdings section
        tk.Label(root, text="TOP HOLDINGS", bg=BG, fg=MUTED, font=FONT_SM).pack(anchor=tk.W)
        tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X, pady=(2, 6))

        self._holdings = tk.Frame(root, bg=BG)
        self._holdings.pack(fill=tk.X)

        # timestamp
        self._ts = tk.Label(root, text="Loading…", bg=BG, fg=MUTED, font=FONT_SM)
        self._ts.pack(anchor=tk.W, pady=(10, 0))

    def _kpi_cell(self, row: int, col: int, label: str, value: str, delta: str = ""):
        cell = tk.Frame(self._kpi, bg=BG2, padx=10, pady=8)
        cell.grid(row=row, column=col, sticky="ew",
                  padx=(0 if col == 0 else 4, 0), pady=(0 if row == 0 else 4, 0))
        tk.Label(cell, text=label, bg=BG2, fg=MUTED, font=FONT_SM, anchor=tk.W).pack(fill=tk.X)
        tk.Label(cell, text=value, bg=BG2, fg=FG, font=FONT_LG, anchor=tk.W).pack(fill=tk.X)
        if delta:
            try:
                num = float(delta.replace("%", "").replace("+", ""))
                colour = GREEN if num >= 0 else RED
            except ValueError:
                colour = MUTED
            tk.Label(cell, text=delta, bg=BG2, fg=colour, font=FONT_SM, anchor=tk.W).pack(fill=tk.X)

    def _holding_row(self, ticker: str, value: str, pnl_pct: float):
        row = tk.Frame(self._holdings, bg=BG)
        row.pack(fill=tk.X, pady=1)
        colour = GREEN if pnl_pct >= 0 else RED
        tk.Label(row, text=_clean(ticker), bg=BG, fg=FG, font=FONT, anchor=tk.W, width=14).pack(side=tk.LEFT)
        tk.Label(row, text=f"{pnl_pct:+.1f}%", bg=BG, fg=colour, font=FONT_SM, width=7, anchor=tk.E).pack(side=tk.RIGHT)
        tk.Label(row, text=value, bg=BG, fg=FG, font=FONT, anchor=tk.E).pack(side=tk.RIGHT)

    # ── Data flow ─────────────────────────────────────────────────────────────
    def _start_fetch(self):
        self._refresh_btn.config(fg=ACCENT)
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        try:
            summary, positions = _fetch_data()
            self.after(0, lambda: self._update(summary, positions))
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _schedule(self):
        self.after(REFRESH, lambda: (self._start_fetch(), self._schedule()))

    def _update(self, summary: dict, positions: list):
        self._refresh_btn.config(fg=MUTED)
        sym = {"GBP": "£", "USD": "$", "EUR": "€"}.get(summary.get("currency", ""), "£")

        total    = float(summary.get("total",    0))
        free     = float(summary.get("free",     0))
        invested = float(summary.get("invested", 0))
        ppl      = sum(float(p.get("ppl", 0)) for p in positions)
        cost_basis = sum(
            float(p.get("quantity", 0)) * float(p.get("averagePrice", 0))
            for p in positions
        )
        ppl_pct  = (ppl / cost_basis * 100) if cost_basis else 0.0

        # Clear and redraw KPIs
        for w in self._kpi.winfo_children():
            w.destroy()

        self._kpi_cell(0, 0, "Total Value",  _fmt(total, sym))
        self._kpi_cell(0, 1, "Free Cash",    _fmt(free,  sym))
        self._kpi_cell(1, 0, "P&L",          _fmt(ppl, sym), f"{ppl_pct:+.2f}%")
        self._kpi_cell(1, 1, "Positions",    str(len(positions)))

        # Clear and redraw holdings
        for w in self._holdings.winfo_children():
            w.destroy()

        sorted_pos = sorted(
            positions,
            key=lambda p: float(p.get("quantity", 0)) * float(p.get("currentPrice", 0)),
            reverse=True,
        )
        for p in sorted_pos[:8]:
            qty   = float(p.get("quantity", 0))
            price = float(p.get("currentPrice", 0))
            avg   = float(p.get("averagePrice", 0))
            val   = qty * price
            cost  = qty * avg
            pct   = ((val - cost) / cost * 100) if cost else 0.0
            self._holding_row(p.get("ticker", ""), _fmt(val, sym), pct)

        self._ts.config(text=f"Updated {datetime.now().strftime('%H:%M:%S')}")

    def _on_error(self, msg: str):
        self._refresh_btn.config(fg=RED)
        self._ts.config(text=f"Error: {msg[:45]}")


if __name__ == "__main__":
    PortfolioWidget().mainloop()
