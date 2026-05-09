import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import COLOR_PRIMARY, vnd, fmt_int, pct


# =========================
# STYLE HELPERS — đồng bộ với Overview & Category

BLUE = "#1A94FF"
BLUE_DARK = "#0B63CE"
CYAN = "#38BDF8"
ORANGE = "#F59E0B"
GREEN = "#22C55E"
PURPLE = "#A78BFA"
RED = "#F87171"
TEXT = "rgba(255,255,255,0.88)"
MUTED = "rgba(255,255,255,0.62)"
GRID = "rgba(255,255,255,0.10)"
CARD_BG = "rgba(255,255,255,0.035)"


def wrap_label(text, width=16):
    if pd.isna(text):
        return "Không xác định"
    return "<br>".join(textwrap.wrap(str(text), width=width))


def clean_label(text, width=28):
    if pd.isna(text):
        return "Không xác định"
    value = str(text)
    if len(value) <= width:
        return value
    return value[: width - 3] + "..."


def shorten_money(value):
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


def style_chart(fig, height=430, legend_top=False, x_tickangle=0, hovermode="x unified"):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT, size=12),
        title=dict(
            x=0.02,
            xanchor="left",
            font=dict(size=17, color="white"),
        ),
        margin=dict(l=20, r=20, t=65, b=80),
        hovermode=hovermode,
        xaxis=dict(
            title_font=dict(color=MUTED),
            tickfont=dict(color=MUTED),
            gridcolor=GRID,
            zeroline=False,
            tickangle=x_tickangle,
            automargin=True,
        ),
        yaxis=dict(
            title_font=dict(color=MUTED),
            tickfont=dict(color=MUTED),
            gridcolor=GRID,
            zeroline=False,
            automargin=True,
        ),
    )

    if legend_top:
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="right",
                x=1,
                font=dict(size=11),
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
                font=dict(size=11),
            )
        )

    return fig


def render_section_title(title, desc=None):
    st.markdown(
        f"""
        <div style="
            margin-top: 18px;
            margin-bottom: 12px;
            padding: 14px 16px;
            border-radius: 16px;
            background: linear-gradient(90deg, rgba(26,148,255,0.16), rgba(255,255,255,0.035));
            border: 1px solid rgba(255,255,255,0.08);
        ">
            <div style="font-size: 1.05rem; font-weight: 800; color: white;">
                {title}
            </div>
            <div style="font-size: 0.86rem; color: rgba(255,255,255,0.62); margin-top: 4px;">
                {desc or ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label, value, sub=""):
    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.045);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 18px;
            padding: 16px 16px 14px 16px;
            min-height: 118px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.18);
        ">
            <div style="
                color: rgba(255,255,255,0.62);
                font-size: 0.82rem;
                margin-bottom: 6px;
            ">
                {label}
            </div>
            <div style="
                color: white;
                font-weight: 800;
                font-size: 1.2rem;
                line-height: 1.25;
            ">
                {value}
            </div>
            <div style="
                color: rgba(255,255,255,0.50);
                font-size: 0.78rem;
                margin-top: 8px;
            ">
                {sub}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_seller_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Phân tích người bán")

    st.markdown(
        """
        <div style="
            color: rgba(255,255,255,0.68);
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 14px;
        ">
            Trang này phân tích hiệu quả hoạt động của người bán trong hệ thống:
            quy mô gian hàng, danh mục sản phẩm, sức bán, doanh thu ước tính,
            chất lượng đánh giá, chính sách giá, discount và coupon.
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = mart_filtered.copy()

    if df.empty:
        st.warning("Không có dữ liệu sau khi áp dụng bộ lọc.")
        return

    # =========================
    # CLEAN DATA

    numeric_cols = [
        "sold_quantity",
        "review_count",
        "review_score",
        "current_price",
        "original_price",
        "discount_percent",
        "coupon_discount_amount",
        "seller_rating",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required_cols = ["product_id", "seller_name"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Thiếu cột bắt buộc: {col}")
            return

    if "category_name" not in df.columns:
        df["category_name"] = "Không xác định"

    if "current_price" not in df.columns:
        df["current_price"] = np.nan

    if "discount_percent" not in df.columns:
        df["discount_percent"] = 0

    if "coupon_discount_amount" not in df.columns:
        df["coupon_discount_amount"] = 0

    if "review_score" not in df.columns:
        df["review_score"] = np.nan

    if "seller_rating" not in df.columns:
        df["seller_rating"] = np.nan

    df["seller_name"] = df["seller_name"].fillna("Không xác định")
    df["category_name"] = df["category_name"].fillna("Không xác định")

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["review_count"] = df["review_count"].fillna(0)
    df["coupon_discount_amount"] = pd.to_numeric(
        df["coupon_discount_amount"], errors="coerce"
    ).fillna(0)

    df["has_coupon"] = df["coupon_discount_amount"] > 0

    df["estimated_revenue"] = (
        df["current_price"].fillna(0) * df["sold_quantity"].fillna(0)
    )

    price_valid_df = df[
        df["current_price"].notna() & (df["current_price"] > 0)
    ].copy()

    # =========================
    # SELLER SUMMARY

    seller_summary = (
        df.groupby("seller_name", dropna=False)
        .agg(
            product_count=("product_id", "nunique"),
            category_count=("category_name", "nunique"),
            sold_quantity=("sold_quantity", "sum"),
            review_count=("review_count", "sum"),
            avg_price=("current_price", "mean"),
            median_price=("current_price", "median"),
            avg_discount=("discount_percent", "mean"),
            avg_review_score=("review_score", "mean"),
            avg_seller_rating=("seller_rating", "mean"),
            estimated_revenue=("estimated_revenue", "sum"),
            coupon_rate=("has_coupon", "mean"),
            coupon_product_count=("has_coupon", "sum"),
        )
        .reset_index()
    )

    seller_summary["coupon_product_count"] = (
        seller_summary["coupon_product_count"].fillna(0).astype(int)
    )
    seller_summary["coupon_rate"] = seller_summary["coupon_rate"] * 100

    total_sellers = seller_summary["seller_name"].nunique()
    total_revenue = seller_summary["estimated_revenue"].sum()
    total_sold = seller_summary["sold_quantity"].sum()
    total_products = seller_summary["product_count"].sum()

    seller_summary["revenue_share"] = np.where(
        total_revenue > 0,
        seller_summary["estimated_revenue"] / total_revenue * 100,
        0,
    )

    seller_summary["sold_share"] = np.where(
        total_sold > 0,
        seller_summary["sold_quantity"] / total_sold * 100,
        0,
    )

    seller_summary["product_share"] = np.where(
        total_products > 0,
        seller_summary["product_count"] / total_products * 100,
        0,
    )

    seller_summary["revenue_per_product"] = np.where(
        seller_summary["product_count"] > 0,
        seller_summary["estimated_revenue"] / seller_summary["product_count"],
        0,
    )

    seller_summary["sold_per_product"] = np.where(
        seller_summary["product_count"] > 0,
        seller_summary["sold_quantity"] / seller_summary["product_count"],
        0,
    )

    seller_summary["review_per_product"] = np.where(
        seller_summary["product_count"] > 0,
        seller_summary["review_count"] / seller_summary["product_count"],
        0,
    )

    seller_summary["display_rating"] = seller_summary["avg_seller_rating"].combine_first(
        seller_summary["avg_review_score"]
    )

    seller_summary = seller_summary.sort_values("estimated_revenue", ascending=False)

    # =========================
    # KPI

    st.markdown("#### Chỉ số tổng quan người bán")

    top_revenue_seller = (
        seller_summary.iloc[0]["seller_name"]
        if not seller_summary.empty
        else "—"
    )

    top_sold_seller = (
        seller_summary.sort_values("sold_quantity", ascending=False)
        .iloc[0]["seller_name"]
        if not seller_summary.empty
        else "—"
    )

    avg_seller_rating = seller_summary["display_rating"].dropna().mean()
    avg_coupon_rate = seller_summary["coupon_rate"].dropna().mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card(
            "Số người bán",
            fmt_int(total_sellers),
            f"Tổng sản phẩm: {fmt_int(total_products)}",
        )

    with k2:
        kpi_card(
            "Doanh thu cao nhất",
            clean_label(top_revenue_seller, 28),
            "Người bán dẫn đầu theo doanh thu ước tính",
        )

    with k3:
        kpi_card(
            "Bán nhiều nhất",
            clean_label(top_sold_seller, 28),
            "Người bán dẫn đầu theo lượt bán",
        )

    with k4:
        rating_text = (
            f"{avg_seller_rating:.2f}/5"
            if not np.isnan(avg_seller_rating)
            else "—"
        )
        kpi_card(
            "Rating TB người bán",
            rating_text,
            f"Coupon TB: {avg_coupon_rate:.1f}%",
        )

    st.markdown("---")

    # =========================
    # MT1: QUY MÔ & ĐÓNG GÓP

    render_section_title(
        "Quy mô và mức độ đóng góp của người bán",
        "Xác định người bán đóng góp lớn nhất về doanh thu, lượt bán và tỷ trọng trong toàn hệ thống.",
    )

    c1, c2 = st.columns(2)

    with c1:
        top_seller_revenue = seller_summary.head(10).copy()
        top_seller_revenue["seller_label"] = top_seller_revenue["seller_name"].apply(
            lambda x: wrap_label(x, 18)
        )

        fig1 = px.treemap(
            top_seller_revenue,
            path=["seller_label"],
            values="estimated_revenue",
            color="revenue_share",
            color_continuous_scale=["#0F172A", "#1D4ED8", "#38BDF8"],
            title="Cơ cấu doanh thu ước tính theo người bán",
            hover_data={
                "estimated_revenue": ":,.0f",
                "revenue_share": ":.2f",
                "product_count": ":,.0f",
                "sold_quantity": ":,.0f",
            },
            labels={
                "estimated_revenue": "Doanh thu ước tính",
                "revenue_share": "Tỷ trọng doanh thu (%)",
                "product_count": "Số sản phẩm",
                "sold_quantity": "Lượt bán",
            },
        )

        fig1.update_traces(
            textfont=dict(size=14, color="white"),
            marker=dict(line=dict(color="rgba(255,255,255,0.18)", width=1.2)),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Doanh thu: %{customdata[0]:,.0f} ₫<br>"
                "Tỷ trọng: %{customdata[1]:.2f}%<br>"
                "Số sản phẩm: %{customdata[2]:,.0f}<br>"
                "Lượt bán: %{customdata[3]:,.0f}<extra></extra>"
            ),
        )

        fig1.update_layout(
            template="plotly_dark",
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=CARD_BG,
            font=dict(color=TEXT),
            title=dict(x=0.02, xanchor="left", font=dict(size=17)),
            margin=dict(l=10, r=10, t=65, b=10),
        )

        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        pareto_df = (
            seller_summary
            .sort_values("estimated_revenue", ascending=False)
            .head(10)
            .copy()
        )

        pareto_df["cum_revenue_share"] = (
            pareto_df["estimated_revenue"].cumsum() / total_revenue * 100
            if total_revenue > 0
            else 0
        )

        pareto_df["seller_label"] = pareto_df["seller_name"].apply(
            lambda x: clean_label(x, 32)
        )
        pareto_df["revenue_label"] = pareto_df["estimated_revenue"].apply(shorten_money)
        pareto_df["cum_label"] = (
            pareto_df["cum_revenue_share"].round(1).astype(str) + "%"
        )

        pareto_df = pareto_df.sort_values("estimated_revenue", ascending=True)

        fig2 = go.Figure()

        fig2.add_trace(
            go.Bar(
                y=pareto_df["seller_label"],
                x=pareto_df["estimated_revenue"],
                name="Doanh thu ước tính",
                orientation="h",
                marker=dict(
                    color=BLUE,
                    line=dict(color=BLUE_DARK, width=1.2),
                ),
                text=pareto_df["revenue_label"],
                textposition="outside",
                textfont=dict(color=TEXT, size=11),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Doanh thu: %{x:,.0f} ₫<br>"
                    "Tỷ trọng: %{customdata:.1f}%<extra></extra>"
                ),
                customdata=pareto_df["revenue_share"],
            )
        )

        fig2.add_trace(
            go.Scatter(
                y=pareto_df["seller_label"],
                x=pareto_df["cum_revenue_share"],
                name="Tỷ trọng lũy kế",
                xaxis="x2",
                mode="lines+markers+text",
                text=pareto_df["cum_label"],
                textposition="middle right",
                line=dict(color=ORANGE, width=3),
                marker=dict(
                    size=8,
                    color=ORANGE,
                    line=dict(color="white", width=1),
                ),
                textfont=dict(color=ORANGE, size=11),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Tỷ trọng lũy kế: %{x:.1f}%<extra></extra>"
                ),
            )
        )

        fig2.update_layout(
            title=dict(
                text="Pareto doanh thu theo người bán",
                x=0.02,
                xanchor="left",
                font=dict(size=17, color="white"),
            ),
            template="plotly_dark",
            height=520,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=CARD_BG,
            font=dict(color=TEXT, size=12),
            margin=dict(l=20, r=80, t=85, b=45),
            hovermode="y unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="right",
                x=1,
                font=dict(size=11),
            ),
            xaxis=dict(
                title="Doanh thu ước tính",
                tickformat="~s",
                gridcolor=GRID,
                zeroline=False,
                title_font=dict(color=MUTED),
                tickfont=dict(color=MUTED),
            ),
            xaxis2=dict(
                title="Tỷ trọng lũy kế (%)",
                overlaying="x",
                side="top",
                range=[0, 105],
                showgrid=False,
                zeroline=False,
                title_font=dict(color=MUTED),
                tickfont=dict(color=MUTED),
            ),
            yaxis=dict(
                title="",
                gridcolor="rgba(255,255,255,0.04)",
                zeroline=False,
                tickfont=dict(color=MUTED, size=11),
                automargin=True,
            ),
        )

        st.plotly_chart(fig2, use_container_width=True)

    # =========================
    # MT2: HIỆU QUẢ KINH DOANH

    render_section_title(
        "Hiệu quả kinh doanh của người bán",
        "So sánh doanh thu, lượt bán, số sản phẩm và rating để nhận diện người bán vận hành hiệu quả.",
    )

    c3, c4 = st.columns(2)

    with c3:
        bubble_df = seller_summary[
            (seller_summary["sold_quantity"] > 0)
            & (seller_summary["estimated_revenue"] > 0)
        ].copy()

        if not bubble_df.empty:
            fig3 = px.scatter(
                bubble_df,
                x="sold_quantity",
                y="estimated_revenue",
                size="product_count",
                color="display_rating",
                hover_name="seller_name",
                color_continuous_scale=["#1E1B4B", "#2563EB", "#22C55E"],
                title="Tương quan lượt bán, doanh thu và quy mô sản phẩm",
                labels={
                    "sold_quantity": "Tổng lượt bán",
                    "estimated_revenue": "Doanh thu ước tính",
                    "product_count": "Số sản phẩm",
                    "display_rating": "Rating",
                },
                custom_data=[
                    "product_count",
                    "category_count",
                    "avg_price",
                    "avg_discount",
                    "coupon_rate",
                ],
            )

            fig3.update_traces(
                marker=dict(
                    opacity=0.78,
                    line=dict(width=1, color="rgba(255,255,255,0.45)"),
                ),
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Lượt bán: %{x:,.0f}<br>"
                    "Doanh thu: %{y:,.0f} ₫<br>"
                    "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                    "Số ngành hàng: %{customdata[1]:,.0f}<br>"
                    "Giá TB: %{customdata[2]:,.0f} ₫<br>"
                    "Discount TB: %{customdata[3]:.1f}%<br>"
                    "Tỷ lệ coupon: %{customdata[4]:.1f}%<extra></extra>"
                ),
            )

            fig3 = style_chart(fig3, height=460)
            fig3.update_layout(
                coloraxis_colorbar=dict(
                    title="Rating",
                    tickfont=dict(color=MUTED),
                    title_font=dict(color=MUTED),
                )
            )
            fig3.update_xaxes(title="Tổng lượt bán", tickformat="~s")
            fig3.update_yaxes(title="Doanh thu ước tính", tickformat="~s")

            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để vẽ biểu đồ tương quan.")

    with c4:
        efficiency_df = seller_summary.head(10).copy()
        efficiency_df["seller_label"] = efficiency_df["seller_name"].apply(
            lambda x: clean_label(x, 34)
        )

        plot_df = efficiency_df.sort_values("revenue_per_product")
        plot_df["revenue_per_product_label"] = plot_df["revenue_per_product"].apply(
            shorten_money
        )

        fig4 = px.bar(
            plot_df,
            x="revenue_per_product",
            y="seller_label",
            orientation="h",
            text="revenue_per_product_label",
            color="revenue_per_product",
            color_continuous_scale=["#0F172A", "#0EA5E9", "#22C55E"],
            title="Hiệu quả doanh thu ước tính trên mỗi sản phẩm",
            labels={
                "revenue_per_product": "Doanh thu ước tính / sản phẩm",
                "seller_label": "Người bán",
            },
            custom_data=[
                "product_count",
                "sold_per_product",
                "display_rating",
                "estimated_revenue",
            ],
        )

        fig4.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            marker_line_color="rgba(255,255,255,0.18)",
            marker_line_width=1,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Doanh thu/SP: %{x:,.0f} ₫<br>"
                "Tổng doanh thu: %{customdata[3]:,.0f} ₫<br>"
                "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                "Sold/SP: %{customdata[1]:,.2f}<br>"
                "Rating: %{customdata[2]:.2f}<extra></extra>"
            ),
        )

        fig4 = style_chart(fig4, height=460, hovermode="y unified")
        fig4.update_layout(showlegend=False, coloraxis_showscale=False)
        fig4.update_xaxes(tickformat="~s")

        st.plotly_chart(fig4, use_container_width=True)

    # =========================
    # MT3: DANH MỤC & ĐỘ PHỦ NGÀNH HÀNG

    render_section_title(
        "Quy mô danh mục và độ phủ ngành hàng",
        "Phân tích người bán theo số lượng sản phẩm, số ngành hàng tham gia và mức độ tập trung danh mục.",
    )

    c5, c6 = st.columns(2)

    with c5:
        catalog_df = (
            seller_summary
            .sort_values("product_count", ascending=False)
            .head(10)
            .copy()
        )

        catalog_df["seller_label"] = catalog_df["seller_name"].apply(
            lambda x: clean_label(x, 34)
        )

        plot_catalog_df = catalog_df.sort_values("product_count")
        plot_catalog_df["product_label"] = plot_catalog_df["product_count"].apply(fmt_int)

        fig5 = px.bar(
            plot_catalog_df,
            x="product_count",
            y="seller_label",
            orientation="h",
            text="product_label",
            color="category_count",
            color_continuous_scale=["#1E1B4B", "#2563EB", "#38BDF8"],
            title="Top người bán theo quy mô danh mục sản phẩm",
            labels={
                "product_count": "Số sản phẩm",
                "seller_label": "Người bán",
                "category_count": "Số ngành hàng",
            },
            custom_data=[
                "category_count",
                "sold_quantity",
                "estimated_revenue",
                "display_rating",
            ],
        )

        fig5.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            marker_line_color="rgba(255,255,255,0.18)",
            marker_line_width=1,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Số sản phẩm: %{x:,.0f}<br>"
                "Số ngành hàng: %{customdata[0]:,.0f}<br>"
                "Lượt bán: %{customdata[1]:,.0f}<br>"
                "Doanh thu: %{customdata[2]:,.0f} ₫<br>"
                "Rating: %{customdata[3]:.2f}<extra></extra>"
            ),
        )

        fig5 = style_chart(fig5, height=460, hovermode="y unified")
        fig5.update_layout(
            showlegend=False,
            coloraxis_colorbar=dict(
                title="Số ngành hàng",
                tickfont=dict(color=MUTED),
                title_font=dict(color=MUTED),
            ),
        )

        st.plotly_chart(fig5, use_container_width=True)

    with c6:
        coverage_df = seller_summary[
            (seller_summary["product_count"] > 0)
            & (seller_summary["category_count"] > 0)
        ].copy()

        if not coverage_df.empty:
            coverage_df["product_size_group"] = pd.cut(
                coverage_df["product_count"],
                bins=[0, 5, 20, 100, 500, np.inf],
                labels=[
                    "1–5 SP",
                    "6–20 SP",
                    "21–100 SP",
                    "101–500 SP",
                    ">500 SP",
                ],
                include_lowest=True,
            )

            coverage_df["category_coverage_group"] = pd.cut(
                coverage_df["category_count"],
                bins=[0, 1, 3, 6, np.inf],
                labels=[
                    "1 ngành",
                    "2–3 ngành",
                    "4–6 ngành",
                    ">6 ngành",
                ],
                include_lowest=True,
            )

            heatmap_df = (
                coverage_df
                .groupby(
                    ["category_coverage_group", "product_size_group"],
                    observed=False
                )
                .agg(
                    seller_count=("seller_name", "nunique"),
                    product_count=("product_count", "sum"),
                    sold_quantity=("sold_quantity", "sum"),
                    estimated_revenue=("estimated_revenue", "sum"),
                    avg_rating=("display_rating", "mean"),
                    avg_sold_per_product=("sold_per_product", "mean"),
                )
                .reset_index()
            )

            product_order = [
                "1–5 SP",
                "6–20 SP",
                "21–100 SP",
                "101–500 SP",
                ">500 SP",
            ]

            category_order = [
                "1 ngành",
                "2–3 ngành",
                "4–6 ngành",
                ">6 ngành",
            ]

            pivot_seller = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="seller_count"
                )
                .reindex(index=category_order, columns=product_order)
                .fillna(0)
            )

            pivot_product = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="product_count"
                )
                .reindex(index=category_order, columns=product_order)
                .fillna(0)
            )

            pivot_sold = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="sold_quantity"
                )
                .reindex(index=category_order, columns=product_order)
                .fillna(0)
            )

            pivot_revenue = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="estimated_revenue"
                )
                .reindex(index=category_order, columns=product_order)
                .fillna(0)
            )

            pivot_rating = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="avg_rating"
                )
                .reindex(index=category_order, columns=product_order)
            )

            pivot_sold_per_product = (
                heatmap_df
                .pivot(
                    index="category_coverage_group",
                    columns="product_size_group",
                    values="avg_sold_per_product"
                )
                .reindex(index=category_order, columns=product_order)
            )

            customdata = np.stack(
                [
                    pivot_seller.values,
                    pivot_product.values,
                    pivot_sold.values,
                    pivot_revenue.values,
                    pivot_rating.fillna(0).values,
                    pivot_sold_per_product.fillna(0).values,
                ],
                axis=-1,
            )

            fig6 = go.Figure(
                data=go.Heatmap(
                    z=pivot_seller.values,
                    x=product_order,
                    y=category_order,
                    customdata=customdata,
                    colorscale=[
                        [0.0, "#111827"],
                        [0.35, "#0EA5E9"],
                        [0.70, "#22C55E"],
                        [1.0, "#F59E0B"],
                    ],
                    colorbar=dict(
                        title="Số người bán",
                        tickfont=dict(color=MUTED),
                        title_font=dict(color=MUTED),
                    ),
                    hovertemplate=(
                        "<b>%{y} · %{x}</b><br>"
                        "Số người bán: %{customdata[0]:,.0f}<br>"
                        "Tổng sản phẩm: %{customdata[1]:,.0f}<br>"
                        "Tổng lượt bán: %{customdata[2]:,.0f}<br>"
                        "Doanh thu ước tính: %{customdata[3]:,.0f} ₫<br>"
                        "Rating TB: %{customdata[4]:.2f}<br>"
                        "Sold/SP TB: %{customdata[5]:.2f}"
                        "<extra></extra>"
                    ),
                )
            )

            fig6 = style_chart(fig6, height=460)

            fig6.update_layout(
                title="Phân bố người bán theo quy mô sản phẩm và độ phủ ngành hàng",
                margin=dict(l=20, r=20, t=70, b=70),
            )

            fig6.update_xaxes(title="Quy mô danh mục sản phẩm")
            fig6.update_yaxes(title="Độ phủ ngành hàng")

            st.plotly_chart(fig6, use_container_width=True)

        else:
            st.info("Không đủ dữ liệu danh mục để hiển thị.")

    # =========================
    # MT4: GIÁ, DISCOUNT & COUPON

    render_section_title(
        "Chiến lược giá, discount và coupon của người bán",
        "So sánh chính sách giá và ưu đãi để xem người bán nào đang phụ thuộc nhiều vào khuyến mãi.",
    )

    c7, c8 = st.columns(2)

    with c7:
        top_price_sellers = (
            seller_summary
            .sort_values("product_count", ascending=False)
            .head(8)["seller_name"]
            .tolist()
        )

        box_df = price_valid_df[
            price_valid_df["seller_name"].isin(top_price_sellers)
        ].copy()

        if not box_df.empty:
            upper_price = box_df["current_price"].quantile(0.97)
            box_df = box_df[box_df["current_price"] <= upper_price]
            box_df["seller_label"] = box_df["seller_name"].apply(
                lambda x: clean_label(x, 32)
            )

            fig7 = px.box(
                box_df,
                x="current_price",
                y="seller_label",
                color="seller_label",
                points=False,
                title="Phân bố giá bán theo người bán phổ biến",
                labels={
                    "current_price": "Giá hiện tại",
                    "seller_label": "Người bán",
                },
            )

            fig7.update_traces(
                marker=dict(opacity=0.75),
                line=dict(width=1.4),
                hovertemplate="<b>%{y}</b><br>Giá: %{x:,.0f} ₫<extra></extra>",
            )

            fig7 = style_chart(fig7, height=470, hovermode="y unified")
            fig7.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=70, b=70),
            )
            fig7.update_xaxes(tickformat="~s")

            st.plotly_chart(fig7, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu giá để hiển thị.")

    with c8:
        promo_df = seller_summary[
            (seller_summary["product_count"] > 0)
            & (seller_summary["sold_quantity"] > 0)
        ].copy()

        if not promo_df.empty:
            fig8 = px.scatter(
                promo_df,
                x="coupon_rate",
                y="avg_discount",
                size="sold_quantity",
                color="estimated_revenue",
                hover_name="seller_name",
                color_continuous_scale=["#1E1B4B", "#2563EB", "#F59E0B", "#EF4444"],
                title="Coupon, discount và sức bán theo người bán",
                labels={
                    "coupon_rate": "Tỷ lệ coupon (%)",
                    "avg_discount": "Discount TB (%)",
                    "sold_quantity": "Tổng lượt bán",
                    "estimated_revenue": "Doanh thu ước tính",
                },
                custom_data=[
                    "product_count",
                    "sold_quantity",
                    "estimated_revenue",
                    "display_rating",
                ],
            )

            fig8.update_traces(
                marker=dict(
                    opacity=0.78,
                    line=dict(width=1, color="rgba(255,255,255,0.45)"),
                ),
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Tỷ lệ coupon: %{x:.1f}%<br>"
                    "Discount TB: %{y:.1f}%<br>"
                    "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                    "Lượt bán: %{customdata[1]:,.0f}<br>"
                    "Doanh thu: %{customdata[2]:,.0f} ₫<br>"
                    "Rating: %{customdata[3]:.2f}<extra></extra>"
                ),
            )

            fig8 = style_chart(fig8, height=470)
            fig8.update_layout(
                coloraxis_colorbar=dict(
                    title="Doanh thu",
                    tickfont=dict(color=MUTED),
                    title_font=dict(color=MUTED),
                )
            )
            fig8.update_xaxes(title="Tỷ lệ coupon (%)")
            fig8.update_yaxes(title="Discount TB (%)")

            st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu ưu đãi để hiển thị.")

    # =========================
    # MT5: CHẤT LƯỢNG & RỦI RO

    render_section_title(
        "Chất lượng đánh giá và nhóm người bán cần chú ý",
        "Nhận diện người bán doanh thu cao nhưng rating thấp, hoặc có nhiều review nhưng chất lượng phản hồi chưa tốt.",
    )

    c9, c10 = st.columns(2)

    with c9:
        rating_df = seller_summary[
            seller_summary["display_rating"].notna()
        ].copy()

        rating_df["rating_group"] = pd.cut(
            rating_df["display_rating"],
            bins=[-0.01, 3, 4, 4.5, 5],
            labels=[
                "≤ 3 sao",
                "3–4 sao",
                "4–4.5 sao",
                "4.5–5 sao",
            ],
            include_lowest=True,
        )

        rating_summary = (
            rating_df.groupby("rating_group", observed=False)
            .agg(
                seller_count=("seller_name", "nunique"),
                product_count=("product_count", "sum"),
                sold_quantity=("sold_quantity", "sum"),
                estimated_revenue=("estimated_revenue", "sum"),
            )
            .reset_index()
        )

        rating_summary["seller_label"] = rating_summary["seller_count"].apply(fmt_int)

        fig9 = px.bar(
            rating_summary,
            x="rating_group",
            y="seller_count",
            text="seller_label",
            title="Cơ cấu người bán theo nhóm rating",
            color="rating_group",
            color_discrete_map={
                "≤ 3 sao": RED,
                "3–4 sao": ORANGE,
                "4–4.5 sao": CYAN,
                "4.5–5 sao": GREEN,
            },
            labels={
                "rating_group": "Nhóm rating",
                "seller_count": "Số người bán",
            },
            custom_data=[
                "product_count",
                "sold_quantity",
                "estimated_revenue",
            ],
        )

        fig9.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=12),
            marker_line_color="rgba(255,255,255,0.16)",
            marker_line_width=0.8,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Số người bán: %{y:,.0f}<br>"
                "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                "Lượt bán: %{customdata[1]:,.0f}<br>"
                "Doanh thu: %{customdata[2]:,.0f} ₫<extra></extra>"
            ),
        )

        fig9 = style_chart(fig9, height=430, legend_top=True)
        fig9.update_layout(showlegend=False)

        st.plotly_chart(fig9, use_container_width=True)

    with c10:
        risk_df = seller_summary.copy()

        revenue_threshold = risk_df["estimated_revenue"].quantile(0.70)
        rating_threshold = 4.0

        risk_df["risk_group"] = np.select(
            [
                (risk_df["estimated_revenue"] >= revenue_threshold)
                & (risk_df["display_rating"] < rating_threshold),
                (risk_df["estimated_revenue"] >= revenue_threshold)
                & (risk_df["display_rating"] >= rating_threshold),
                (risk_df["estimated_revenue"] < revenue_threshold)
                & (risk_df["display_rating"] >= rating_threshold),
            ],
            [
                "Doanh thu cao - Rating thấp",
                "Doanh thu cao - Rating tốt",
                "Doanh thu thấp - Rating tốt",
            ],
            default="Doanh thu thấp - Rating thấp",
        )

        risk_plot_df = risk_df[
            (risk_df["estimated_revenue"] > 0)
            & (risk_df["display_rating"].notna())
        ].copy()

        if not risk_plot_df.empty:
            fig10 = px.scatter(
                risk_plot_df,
                x="display_rating",
                y="estimated_revenue",
                size="review_count",
                color="risk_group",
                hover_name="seller_name",
                color_discrete_map={
                    "Doanh thu cao - Rating thấp": RED,
                    "Doanh thu cao - Rating tốt": GREEN,
                    "Doanh thu thấp - Rating tốt": CYAN,
                    "Doanh thu thấp - Rating thấp": "rgba(255,255,255,0.45)",
                },
                title="Ma trận doanh thu và chất lượng người bán",
                labels={
                    "display_rating": "Rating",
                    "estimated_revenue": "Doanh thu ước tính",
                    "review_count": "Số review",
                    "risk_group": "Nhóm người bán",
                },
                custom_data=[
                    "product_count",
                    "sold_quantity",
                    "avg_discount",
                    "coupon_rate",
                ],
            )

            fig10.update_traces(
                marker=dict(
                    opacity=0.82,
                    line=dict(width=1, color="rgba(255,255,255,0.5)"),
                ),
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Rating: %{x:.2f}<br>"
                    "Doanh thu: %{y:,.0f} ₫<br>"
                    "Số review: %{marker.size:,.0f}<br>"
                    "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                    "Lượt bán: %{customdata[1]:,.0f}<br>"
                    "Discount TB: %{customdata[2]:.1f}%<br>"
                    "Tỷ lệ coupon: %{customdata[3]:.1f}%<extra></extra>"
                ),
            )

            fig10.add_vline(
                x=rating_threshold,
                line_dash="dash",
                line_color="rgba(255,255,255,0.45)",
                annotation_text="Rating 4.0",
                annotation_font_color=TEXT,
            )

            fig10.add_hline(
                y=revenue_threshold,
                line_dash="dash",
                line_color="rgba(255,255,255,0.45)",
                annotation_text="Top 30% doanh thu",
                annotation_font_color=TEXT,
            )

            fig10 = style_chart(fig10, height=430)
            fig10.update_layout(margin=dict(l=20, r=20, t=70, b=110))
            fig10.update_xaxes(range=[0, 5.1])
            fig10.update_yaxes(tickformat="~s")

            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để hiển thị ma trận rủi ro.")

    # =========================
    # TABLE

    render_section_title(
        "Bảng tổng hợp hiệu quả người bán",
        "Bảng số liệu chi tiết để đối chiếu các biểu đồ phía trên.",
    )

    table_df = seller_summary.copy()

    table_df["avg_price"] = table_df["avg_price"].round(0)
    table_df["median_price"] = table_df["median_price"].round(0)
    table_df["avg_discount"] = table_df["avg_discount"].round(2)
    table_df["avg_review_score"] = table_df["avg_review_score"].round(2)
    table_df["avg_seller_rating"] = table_df["avg_seller_rating"].round(2)
    table_df["display_rating"] = table_df["display_rating"].round(2)
    table_df["estimated_revenue"] = table_df["estimated_revenue"].round(0)
    table_df["revenue_share"] = table_df["revenue_share"].round(2)
    table_df["sold_share"] = table_df["sold_share"].round(2)
    table_df["coupon_rate"] = table_df["coupon_rate"].round(2)
    table_df["coupon_product_count"] = table_df["coupon_product_count"].astype(int)
    table_df["revenue_per_product"] = table_df["revenue_per_product"].round(0)
    table_df["sold_per_product"] = table_df["sold_per_product"].round(2)
    table_df["review_per_product"] = table_df["review_per_product"].round(2)

    table_df = table_df.rename(
        columns={
            "seller_name": "Người bán",
            "product_count": "Số sản phẩm",
            "category_count": "Số ngành hàng",
            "sold_quantity": "Lượt bán",
            "sold_share": "Tỷ trọng sold (%)",
            "review_count": "Số review",
            "avg_price": "Giá TB",
            "median_price": "Giá trung vị",
            "avg_discount": "Discount TB (%)",
            "avg_review_score": "Review score TB",
            "avg_seller_rating": "Seller rating TB",
            "display_rating": "Rating hiển thị",
            "estimated_revenue": "Doanh thu ước tính",
            "revenue_share": "Tỷ trọng doanh thu (%)",
            "coupon_rate": "Tỷ lệ coupon (%)",
            "coupon_product_count": "Số SP có coupon",
            "revenue_per_product": "Doanh thu / sản phẩm",
            "sold_per_product": "Sold / sản phẩm",
            "review_per_product": "Review / sản phẩm",
        }
    )

    st.dataframe(
        table_df[
            [
                "Người bán",
                "Số sản phẩm",
                "Số ngành hàng",
                "Số SP có coupon",
                "Lượt bán",
                "Tỷ trọng sold (%)",
                "Số review",
                "Giá TB",
                "Giá trung vị",
                "Discount TB (%)",
                "Tỷ lệ coupon (%)",
                "Rating hiển thị",
                "Doanh thu ước tính",
                "Tỷ trọng doanh thu (%)",
                "Doanh thu / sản phẩm",
                "Sold / sản phẩm",
                "Review / sản phẩm",
            ]
        ],
        use_container_width=True,
        height=430,
    )
