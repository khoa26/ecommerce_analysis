from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import fmt_int, pct
from components.chart_utils import money_short, clean_label, plot_chart, section


BLUE = "#1A94FF"
CYAN = "#38BDF8"
GREEN = "#22C55E"
ORANGE = "#F59E0B"


RATING_HELP = (
    "Product rating = review_score trong bảng product; "
    "Review rating = trung bình rating_score từ bảng review; "
    "Seller rating = seller_rating của người bán."
)


def kpi(label: str, value: str, sub: str = ""):
    html = (
        '<div style="'
        'background:rgba(255,255,255,0.045);'
        'border:1px solid rgba(255,255,255,0.10);'
        'border-radius:18px;'
        'padding:16px;'
        'min-height:112px;'
        'box-shadow:0 8px 30px rgba(0,0,0,0.18);'
        '">'
        f'<div style="color:rgba(255,255,255,0.62);font-size:0.82rem;margin-bottom:6px;">{label}</div>'
        f'<div style="color:white;font-weight:800;font-size:1.2rem;line-height:1.25;">{value}</div>'
        f'<div style="color:rgba(255,255,255,0.50);font-size:0.78rem;margin-top:8px;">{sub}</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)




def build_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    cat = (
        df.groupby("category_name", dropna=False)
        .agg(
            product_count=("product_id", "nunique"),
            seller_count=("seller_id", "nunique"),
            sold_quantity=("sold_quantity", "sum"),
            estimated_revenue=("estimated_revenue", "sum"),
            avg_price=("current_price", "mean"),
            avg_discount=("discount_percent", "mean"),
            coupon_rate=("has_coupon", "mean"),
            product_rating=("product_rating", "mean"),
            review_rating=("review_rating", "mean"),
            seller_rating=("seller_rating_clean", "mean"),
        )
        .reset_index()
    )

    cat["category_label"] = cat["category_name"].apply(lambda x: clean_label(x, 30))

    return cat


def render_overview_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Tổng quan hệ thống thương mại điện tử")

    st.markdown(
        (
            '<div style="'
            'color:rgba(255,255,255,0.68);'
            'font-size:0.95rem;'
            'line-height:1.6;'
            'margin-bottom:14px;'
            '">'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    df = mart_filtered.copy()

    if df.empty:
        st.warning("Không có dữ liệu sau khi áp dụng bộ lọc.")
        return

    required_cols = [
        "product_id",
        "seller_id",
        "category_name",
        "sold_quantity",
        "current_price",
        "discount_percent",
        "product_rating",
        "review_rating",
        "seller_rating_clean",
        "estimated_revenue",
        "has_discount",
        "has_coupon",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(
            "Thiếu cột trong mart: "
            + ", ".join(missing_cols)
            + ". Hãy kiểm tra lại phần build_mart trước."
        )
        return

    # Ép kiểu an toàn
    numeric_cols = [
        "sold_quantity",
        "current_price",
        "discount_percent",
        "product_rating",
        "review_rating",
        "seller_rating_clean",
        "estimated_revenue",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["current_price"] = df["current_price"].fillna(0)
    df["estimated_revenue"] = df["estimated_revenue"].fillna(0)
    df["has_coupon"] = df["has_coupon"].fillna(False).astype(bool)
    df["has_discount"] = df["has_discount"].fillna(False).astype(bool)
    df["category_name"] = df["category_name"].fillna("Không xác định")

    # =============================
    # KPI TỔNG QUAN
    # =============================
    total_revenue = df["estimated_revenue"].sum()
    total_sold = df["sold_quantity"].sum()

    avg_product_rating = df["product_rating"].dropna().mean()
    avg_review_rating = df["review_rating"].dropna().mean()
    avg_seller_rating = df["seller_rating_clean"].dropna().mean()

    coupon_rate = df["has_coupon"].mean()
    discount_rate = df["has_discount"].mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
         kpi(
            "Doanh thu ước tính",
            money_short(total_revenue),
           
        )

    with k2:
        kpi(
            "Lượt bán",
            fmt_int(total_sold),
           
        )

    with k3:
        kpi(
            "Tỷ lệ có coupon",
            pct(coupon_rate * 100),
           
        )
    with k4:
        kpi(
            "Điểm đánh giá trung bình của sản phẩm",
            f"{avg_product_rating:.2f}/5" if pd.notna(avg_product_rating) else "—",
           
        )

  

    # =============================
    # SUMMARY THEO CATEGORY
    # =============================
    cat = build_category_summary(df)

    # =============================
    # CHART 1: TOP CATEGORY THEO DOANH THU
    # =============================
    section(
        "1. Cơ cấu doanh thu theo ngành hàng",
        "Mục tiêu: nhìn nhanh ngành hàng nào đang đóng góp nhiều nhất cho toàn hệ thống.",
    )

    top_cat = cat.sort_values("estimated_revenue", ascending=False).head(8)

    if top_cat.empty:
        st.info("Không đủ dữ liệu ngành hàng để vẽ biểu đồ.")
    else:
        fig = go.Figure()

        fig.add_bar(
            x=top_cat["category_label"],
            y=top_cat["estimated_revenue"],
            marker_color=BLUE,
            text=top_cat["estimated_revenue"].map(money_short),
            textposition="outside",
            customdata=np.stack(
                [
                    top_cat["sold_quantity"],
                    top_cat["product_count"],
                    top_cat["review_rating"].round(2),
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Doanh thu: %{y:,.0f} đ"
                "<br>Lượt bán: %{customdata[0]:,.0f}"
                "<br>Số sản phẩm: %{customdata[1]:,.0f}"
                "<br>Review rating: %{customdata[2]:.2f}/5"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            title="Top ngành hàng theo doanh thu ước tính",
            showlegend=False,
        )
        fig.update_xaxes(title="Ngành hàng", tickangle=-25)
        fig.update_yaxes(title="Doanh thu ước tính", tickformat="~s")

        plot_chart(fig, height=460)



    # =============================
    # CHART 2: PHÂN BỐ REVIEW RATING
    # =============================
    section(
        "2. Phân bố chất lượng đánh giá sản phẩm",
        "Mục tiêu: xem hệ thống đang tập trung nhiều ở nhóm rating thấp hay cao.",
    )

    rating_df = df[df["review_rating"].notna()].copy()

    if rating_df.empty:
        st.info("Không đủ dữ liệu review_rating để vẽ biểu đồ.")
    else:
        bins = [0, 2, 3, 4, 4.5, 5]
        labels = ["≤2 sao", "2–3 sao", "3–4 sao", "4–4.5 sao", "4.5–5 sao"]

        rating_df["rating_group"] = pd.cut(
            rating_df["review_rating"],
            bins=bins,
            labels=labels,
            include_lowest=True,
        )

        rating_group = (
            rating_df.groupby("rating_group", observed=False)
            .agg(
                product_count=("product_id", "nunique"),
                revenue=("estimated_revenue", "sum"),
                sold=("sold_quantity", "sum"),
            )
            .reset_index()
        )

        fig = go.Figure()

        fig.add_bar(
            x=rating_group["rating_group"].astype(str),
            y=rating_group["product_count"],
            marker_color=GREEN,
            text=rating_group["product_count"],
            textposition="outside",
            customdata=np.stack(
                [
                    rating_group["revenue"].map(money_short),
                    rating_group["sold"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Số sản phẩm: %{y:,.0f}"
                "<br>Doanh thu: %{customdata[0]}"
                "<br>Lượt bán: %{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            title="Số sản phẩm theo nhóm điểm đánh giá",
            showlegend=False,
        )
        fig.update_xaxes(title="Nhóm Review rating")
        fig.update_yaxes(title="Số sản phẩm")

        plot_chart(fig, height=420)

    
    # =============================
    # CHART 3: PARETO DOANH THU
    # =============================
    section(
        "3. Mức độ tập trung doanh thu theo ngành hàng",
        "Mục tiêu: xem doanh thu có đang tập trung vào một vài ngành hàng chủ lực hay được phân bổ đều trên toàn hệ thống.",
    )

    pareto_df = (
        cat[cat["estimated_revenue"] > 0]
        .sort_values("estimated_revenue", ascending=False)
        .head(10)
        .copy()
    )

    if pareto_df.empty:
        st.info("Không đủ dữ liệu để vẽ biểu đồ Pareto.")
    else:
        total_rev = pareto_df["estimated_revenue"].sum()

        pareto_df["cum_revenue"] = pareto_df["estimated_revenue"].cumsum()
        pareto_df["cum_pct"] = np.where(
            total_rev > 0,
            pareto_df["cum_revenue"] / total_rev * 100,
            0,
        )

        fig = go.Figure()

        fig.add_bar(
            x=pareto_df["category_label"],
            y=pareto_df["estimated_revenue"],
            name="Doanh thu ước tính",
            marker_color=BLUE,
            text=pareto_df["estimated_revenue"].map(money_short),
            textposition="outside",
            customdata=np.stack(
                [
                    pareto_df["sold_quantity"],
                    pareto_df["product_count"],
                    pareto_df["cum_pct"].round(1),
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Doanh thu: %{y:,.0f} đ"
                "<br>Lượt bán: %{customdata[0]:,.0f}"
                "<br>Số sản phẩm: %{customdata[1]:,.0f}"
                "<br>Tỷ trọng lũy kế: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
        )

        fig.add_scatter(
            x=pareto_df["category_label"],
            y=pareto_df["cum_pct"],
            name="Tỷ trọng lũy kế (%)",
            mode="lines+markers+text",
            text=pareto_df["cum_pct"].map(lambda x: f"{x:.1f}%"),
            textposition="top center",
            yaxis="y2",
            marker=dict(size=9, color=ORANGE, line=dict(width=1, color="white")),
            line=dict(width=3, color=ORANGE),
            hovertemplate="<b>%{x}</b><br>Tỷ trọng lũy kế: %{y:.1f}%<extra></extra>",
        )

        fig.update_layout(
            title="Pareto doanh thu theo ngành hàng",
            yaxis=dict(
                title="Doanh thu ước tính",
                tickformat="~s",
            ),
            yaxis2=dict(
                title="Tỷ trọng lũy kế (%)",
                overlaying="y",
                side="right",
                range=[0, 105],
                showgrid=False,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

        fig.update_xaxes(title="Ngành hàng", tickangle=-25)

        plot_chart(fig, height=500, hovermode="closest", legend_top=True)

       
    # =============================
    # CHART 4: TỔNG QUAN KHUYẾN MÃI
    # =============================
    section(
        "4. Tổng quan khuyến mãi",
        "Mục tiêu: xem tỷ lệ coupon/discount ở mức hệ thống trước khi phân tích sâu theo ngành và người bán.",
    )

    promo = pd.DataFrame(
        {
            "Loại ưu đãi": [
                "Có coupon",
                "Có discount",
                "Không coupon",
                "Không discount",
            ],
            "Tỷ lệ": [
                coupon_rate * 100,
                discount_rate * 100,
                (1 - coupon_rate) * 100,
                (1 - discount_rate) * 100,
            ],
        }
    )

    fig = go.Figure()

    fig.add_bar(
        x=promo["Loại ưu đãi"],
        y=promo["Tỷ lệ"],
        marker_color=[CYAN, ORANGE, BLUE, GREEN],
        text=promo["Tỷ lệ"].map(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Tỷ lệ: %{y:.1f}%<extra></extra>",
    )

    fig.update_layout(
        title="Tỷ lệ sản phẩm có coupon/discount",
        showlegend=False,
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Tỷ lệ sản phẩm (%)", range=[0, 100])

    plot_chart(fig, height=420)
