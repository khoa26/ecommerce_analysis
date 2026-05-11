import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from textwrap import dedent

PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True
}


def money_short(value):
    if pd.isna(value):
        return "—"

    value = float(value)

    if abs(value) >= 1e12:
        return f"{value / 1e12:.1f}T"
    if abs(value) >= 1e9:
        return f"{value / 1e9:.1f}B"
    if abs(value) >= 1e6:
        return f"{value / 1e6:.1f}M"
    if abs(value) >= 1e3:
        return f"{value / 1e3:.1f}K"

    return f"{value:.0f}"


def clean_label(text, width=28):
    if pd.isna(text) or str(text).strip() == "":
        return "Không xác định"

    text = str(text).strip()
    return text if len(text) <= width else text[:width - 3] + "..."


def style_fig(fig: go.Figure, height=440, hovermode="closest", legend_top=False):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.035)",
        font=dict(color="rgba(255,255,255,0.88)", size=12),
        title=dict(x=0.02, xanchor="left", font=dict(size=17, color="white")),
        margin=dict(l=20, r=20, t=68, b=72),
        hovermode=hovermode,
        hoverlabel=dict(
            bgcolor="rgba(18,24,33,0.96)",
            font_size=12,
        ),
    )

    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        automargin=True,
        showspikes=False,
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        automargin=True,
        showspikes=False,
    )

    if legend_top:
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=1,
            )
        )
    else:
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5,
            )
        )

    return fig


def plot_chart(fig: go.Figure, height=440, hovermode="closest", legend_top=False):
    st.plotly_chart(
        style_fig(fig, height=height, hovermode=hovermode, legend_top=legend_top),
        use_container_width=True,
        config=PLOT_CONFIG,
    )


def section(title, desc=""):
    html = f"""
<div style="
    margin-top:18px;
    margin-bottom:12px;
    padding:14px 16px;
    border-radius:16px;
    background:linear-gradient(90deg,rgba(26,148,255,0.16),rgba(255,255,255,0.035));
    border:1px solid rgba(255,255,255,0.08);
">
    <div style="font-size:1.05rem;font-weight:800;color:white;">
        {title}
    </div>
    <div style="font-size:0.86rem;color:rgba(255,255,255,0.62);margin-top:4px;">
        {desc}
    </div>
</div>
"""
    st.markdown(dedent(html), unsafe_allow_html=True)