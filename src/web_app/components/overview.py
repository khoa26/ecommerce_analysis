import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import COLOR_PRIMARY, vnd, fmt_int, pct



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


def clean_label(text, width=24):
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


def render_overview_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Tổng quan hệ thống thương mại điện tử")

    st.markdown(
        """
        <div style="
            color: rgba(255,255,255,0.68);
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 14px;
        ">
            Trang này cung cấp cái nhìn tổng quan về toàn bộ hệ thống:
            quy mô sản phẩm, ngành hàng, người bán, sức bán, doanh thu ước tính,
            giá bán, ưu đãi và chất lượng phản hồi từ khách hàng.
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = mart_filtered.copy()

    if df.empty:
        st.warning("Không có dữ liệu sau khi áp dụng bộ lọc.")
        return

    

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

    required_cols = ["product_id", "category_name"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Thiếu cột bắt buộc: {col}")
            return

    df["category_name"] = df["category_name"].fillna("Không xác định")

    if "seller_name" not in df.columns:
        df["seller_name"] = "Không xác định"

    if "current_price" not in df.columns:
        df["current_price"] = np.nan

    if "discount_percent" not in df.columns:
        df["discount_percent"] = 0

    if "coupon_discount_amount" not in df.columns:
        df["coupon_discount_amount"] = 0

    if "review_score" not in df.columns:
        df["review_score"] = np.nan

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["review_count"] = df["review_count"].fillna(0)
    df["coupon_discount_amount"] = pd.to_numeric(
        df["coupon_discount_amount"], errors="coerce"
    ).fillna(0)

    df["has_coupon"] = df["coupon_discount_amount"] > 0
    df["estimated_revenue"] = (
        df["current_price"].fillna(0) * df["sold_quantity"].fillna(0)
    )

    # =========================
    # KPI TỔNG QUAN

    st.markdown("#### Chỉ số tổng quan")

    total_products = df["product_id"].nunique()
    total_categories = df["category_name"].nunique()
    total_sellers = df["seller_name"].nunique()
    total_sold = df["sold_quantity"].sum()
    total_reviews = df["review_count"].sum()
    total_revenue = df["estimated_revenue"].sum()

    avg_price = df["current_price"].dropna().mean()
    avg_discount = df["discount_percent"].dropna().mean()
    coupon_rate = df["has_coupon"].mean() * 100
    avg_rating = df["review_score"].dropna().mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card(
            "Sản phẩm",
            fmt_int(total_products),
            f"{fmt_int(total_categories)} ngành hàng",
        )

    with k2:
        kpi_card(
            "Người bán",
            fmt_int(total_sellers),
            f"Tổng sold: {fmt_int(total_sold)}",
        )

    with k3:
        kpi_card(
            "Doanh thu ước tính",
            shorten_money(total_revenue),
            f"Giá TB: {vnd(avg_price)}",
        )

    with k4:
        rating_text = f"{avg_rating:.2f}/5" if not np.isnan(avg_rating) else "—"
        discount_text = f"Discount TB: {avg_discount:.1f}%" if not np.isnan(avg_discount) else "Discount TB: —"
        kpi_card(
            "Đánh giá TB",
            rating_text,
            f"{discount_text} · Coupon: {coupon_rate:.1f}%",
        )

    st.markdown("---")

    # =========================
    # CATEGORY SUMMARY

    category_summary = (
        df.groupby("category_name", dropna=False)
        .agg(
            product_count=("product_id", "nunique"),
            sold_quantity=("sold_quantity", "sum"),
            review_count=("review_count", "sum"),
            avg_price=("current_price", "mean"),
            avg_rating=("review_score", "mean"),
            estimated_revenue=("estimated_revenue", "sum"),
        )
        .reset_index()
    )

    category_summary["revenue_share"] = np.where(
        total_revenue > 0,
        category_summary["estimated_revenue"] / total_revenue * 100,
        0,
    )

    category_summary["sold_share"] = np.where(
        total_sold > 0,
        category_summary["sold_quantity"] / total_sold * 100,
        0,
    )

    # =========================
    # BIỂU ĐỒ 1 + 2

    render_section_title(
        "Bức tranh chung theo ngành hàng",
        "Xem nhanh cơ cấu sản phẩm, doanh thu và sức bán của các ngành hàng nổi bật.",
    )

    c1, c2 = st.columns(2)

    with c1:
        top_category_product = (
            category_summary
            .sort_values("product_count", ascending=False)
            .head(10)
            .copy()
        )

        top_category_product["category_label"] = top_category_product["category_name"].apply(
            lambda x: wrap_label(x, 18)
        )

        fig1 = px.treemap(
            top_category_product,
            path=["category_label"],
            values="product_count",
            color="product_count",
            color_continuous_scale=["#0F172A", "#1D4ED8", "#38BDF8"],
            title="Cơ cấu sản phẩm theo ngành hàng",
            hover_data={
                "product_count": ":,.0f",
                "sold_quantity": ":,.0f",
                "estimated_revenue": ":,.0f",
            },
            labels={
                "product_count": "Số sản phẩm",
                "sold_quantity": "Lượt bán",
                "estimated_revenue": "Doanh thu ước tính",
            },
        )

        fig1.update_traces(
            textfont=dict(size=14, color="white"),
            marker=dict(line=dict(color="rgba(255,255,255,0.18)", width=1.2)),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                "Lượt bán: %{customdata[1]:,.0f}<br>"
                "Doanh thu: %{customdata[2]:,.0f} ₫<extra></extra>"
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
        top_category_sold = (
            category_summary
            .sort_values("sold_quantity", ascending=False)
            .head(10)
            .copy()
        )

        top_category_sold["category_label"] = top_category_sold["category_name"].apply(
            lambda x: clean_label(x, 34)
        )

        plot_sold_df = top_category_sold.sort_values("sold_quantity")
        plot_sold_df["sold_label"] = plot_sold_df["sold_quantity"].apply(
            lambda x: f"{x/1_000_000:.1f}M" if x >= 1_000_000 else fmt_int(x)
        )

        fig2 = px.bar(
            plot_sold_df,
            x="sold_quantity",
            y="category_label",
            orientation="h",
            text="sold_label",
            color="sold_quantity",
            color_continuous_scale=["#0F172A", "#0EA5E9", "#22C55E"],
            title="Top ngành hàng theo lượt bán",
            labels={
                "sold_quantity": "Lượt bán",
                "category_label": "Ngành hàng",
            },
            custom_data=[
                "product_count",
                "review_count",
                "estimated_revenue",
                "sold_share",
            ],
        )

        fig2.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            marker_line_color="rgba(255,255,255,0.18)",
            marker_line_width=1,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Lượt bán: %{x:,.0f}<br>"
                "Tỷ trọng sold: %{customdata[3]:.2f}%<br>"
                "Số sản phẩm: %{customdata[0]:,.0f}<br>"
                "Số review: %{customdata[1]:,.0f}<br>"
                "Doanh thu: %{customdata[2]:,.0f} ₫<extra></extra>"
            ),
        )

        fig2 = style_chart(fig2, height=460, hovermode="y unified")
        fig2.update_layout(showlegend=False, coloraxis_showscale=False)
        fig2.update_xaxes(tickformat="~s")

        st.plotly_chart(fig2, use_container_width=True)

    # =========================
    # GIÁ & ƯU ĐÃI

    render_section_title(
        "Bức tranh chung về giá và ưu đãi",
        "Quan sát phân bố giá bán và tỷ lệ sản phẩm có coupon trong toàn bộ hệ thống.",
    )

    c3, c4 = st.columns(2)

    with c3:
        price_df = df[
            df["current_price"].notna() & (df["current_price"] > 0)
        ].copy()

        if not price_df.empty:
            upper_price = price_df["current_price"].quantile(0.98)
            price_df = price_df[price_df["current_price"] <= upper_price]

            fig3 = px.histogram(
                price_df,
                x="current_price",
                nbins=45,
                title="Phân bố giá sản phẩm",
                color_discrete_sequence=[BLUE],
                labels={"current_price": "Giá hiện tại"},
            )

            fig3.update_traces(
                marker_line_color="rgba(255,255,255,0.16)",
                marker_line_width=0.7,
                hovertemplate="Khoảng giá: %{x:,.0f} ₫<br>Số sản phẩm: %{y:,.0f}<extra></extra>",
            )

            fig3 = style_chart(fig3, height=430)
            fig3.update_layout(showlegend=False)
            fig3.update_xaxes(title="Giá hiện tại", tickformat="~s")
            fig3.update_yaxes(title="Số sản phẩm")

            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu giá để hiển thị.")

    with c4:
        coupon_summary = (
            df.groupby("has_coupon")
            .agg(product_count=("product_id", "nunique"))
            .reset_index()
        )

        coupon_summary["Trạng thái coupon"] = coupon_summary["has_coupon"].map(
            {
                True: "Có coupon",
                False: "Không có coupon",
            }
        )

        coupon_summary["percent"] = (
            coupon_summary["product_count"] / coupon_summary["product_count"].sum() * 100
            if coupon_summary["product_count"].sum() > 0
            else 0
        )

        fig4 = px.pie(
            coupon_summary,
            names="Trạng thái coupon",
            values="product_count",
            hole=0.55,
            title="Tỷ lệ sản phẩm có coupon",
            color="Trạng thái coupon",
            color_discrete_map={
                "Có coupon": PURPLE,
                "Không có coupon": "rgba(255,255,255,0.28)",
            },
        )

        fig4.update_traces(
            textinfo="label+percent",
            textfont=dict(color="white", size=12),
            marker=dict(line=dict(color="rgba(255,255,255,0.12)", width=1)),
            hovertemplate="<b>%{label}</b><br>Số sản phẩm: %{value:,.0f}<br>Tỷ lệ: %{percent}<extra></extra>",
        )

        fig4.update_layout(
            template="plotly_dark",
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=CARD_BG,
            font=dict(color=TEXT),
            title=dict(x=0.02, xanchor="left", font=dict(size=17)),
            margin=dict(l=20, r=20, t=65, b=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
            ),
        )

        st.plotly_chart(fig4, use_container_width=True)

    # =========================
    # RATING

    render_section_title(
        "Cơ cấu sản phẩm theo mức rating",
        "Đánh giá chất lượng phản hồi tổng quan thông qua nhóm điểm review của sản phẩm.",
    )

    rating_df = df.dropna(subset=["review_score"]).copy()

    rating_df["rating_group"] = pd.cut(
        rating_df["review_score"],
        bins=[-0.01, 3, 4, 4.5, 5],
        labels=["≤ 3 sao", "3–4 sao", "4–4.5 sao", "4.5–5 sao"],
        include_lowest=True,
    )

    rating_summary = (
        rating_df.groupby("rating_group", observed=False)
        .agg(
            product_count=("product_id", "nunique"),
            sold_quantity=("sold_quantity", "sum"),
            review_count=("review_count", "sum"),
        )
        .reset_index()
    )

    rating_summary["product_label"] = rating_summary["product_count"].apply(fmt_int)

    fig5 = px.bar(
        rating_summary,
        x="rating_group",
        y="product_count",
        text="product_label",
        title="Cơ cấu sản phẩm theo nhóm điểm đánh giá",
        labels={
            "rating_group": "Nhóm rating",
            "product_count": "Số sản phẩm",
        },
        color="rating_group",
        color_discrete_map={
            "≤ 3 sao": RED,
            "3–4 sao": ORANGE,
            "4–4.5 sao": CYAN,
            "4.5–5 sao": GREEN,
        },
        custom_data=["sold_quantity", "review_count"],
    )

    fig5.update_traces(
        textposition="outside",
        textfont=dict(color=TEXT, size=12),
        marker_line_color="rgba(255,255,255,0.16)",
        marker_line_width=0.8,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Số sản phẩm: %{y:,.0f}<br>"
            "Lượt bán: %{customdata[0]:,.0f}<br>"
            "Số review: %{customdata[1]:,.0f}<extra></extra>"
        ),
    )

    fig5 = style_chart(fig5, height=430, legend_top=True)
    fig5.update_layout(showlegend=False)
    fig5.update_yaxes(title="Số sản phẩm")

    st.plotly_chart(fig5, use_container_width=True)

    # =========================
    # BẢNG TÓM TẮT

    render_section_title(
        "Tóm tắt nhanh theo ngành hàng",
        "Top ngành hàng theo lượt bán để đối chiếu nhanh với các biểu đồ tổng quan.",
    )

    overview_table = (
        category_summary
        .sort_values("sold_quantity", ascending=False)
        .head(10)
        .copy()
    )

    overview_table["avg_price"] = overview_table["avg_price"].round(0)
    overview_table["avg_rating"] = overview_table["avg_rating"].round(2)
    overview_table["estimated_revenue"] = overview_table["estimated_revenue"].round(0)
    overview_table["revenue_share"] = overview_table["revenue_share"].round(2)
    overview_table["sold_share"] = overview_table["sold_share"].round(2)

    overview_table = overview_table.rename(
        columns={
            "category_name": "Ngành hàng",
            "product_count": "Số sản phẩm",
            "sold_quantity": "Lượt bán",
            "sold_share": "Tỷ trọng sold (%)",
            "review_count": "Số review",
            "avg_price": "Giá TB",
            "avg_rating": "Rating TB",
            "estimated_revenue": "Doanh thu ước tính",
            "revenue_share": "Tỷ trọng doanh thu (%)",
        }
    )

    st.dataframe(
        overview_table[
            [
                "Ngành hàng",
                "Số sản phẩm",
                "Lượt bán",
                "Tỷ trọng sold (%)",
                "Số review",
                "Giá TB",
                "Rating TB",
                "Doanh thu ước tính",
                "Tỷ trọng doanh thu (%)",
            ]
        ],
        use_container_width=True,
        height=380,
    )
