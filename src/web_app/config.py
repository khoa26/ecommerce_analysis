from __future__ import annotations
from pathlib import Path
from textwrap import dedent
import streamlit as st

APP_TITLE = "Hệ thống trực quan hóa dữ liệu Thương mại điện tử (Tiki)"

COLOR_PRIMARY = "#1A94FF"  # Tiki blue-ish
COLOR_TEXT_MUTED = "rgba(255,255,255,.7)"

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PROCESSED_POWERBI_DIR = PROCESSED_DIR / "powerbi"

def vnd(x: float | int | None) -> str:
    if x is None:
        return "—"
    try:
        return f"{int(round(float(x))):,} VNĐ".replace(",", ".")
    except Exception:
        return "—"


def pct(x: float | None, digits: int = 1) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.{digits}f}%"
    except Exception:
        return "—"


def fmt_int(x: float | int | None) -> str:
    if x is None:
        return "—"
    try:
        return f"{int(round(float(x))):,}".replace(",", ".")
    except Exception:
        return "—"

def render_kpi(label: str, value: str, sub: str | None = None) -> None:
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    html = f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """
    st.markdown(dedent(html), unsafe_allow_html=True)
