import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import COLOR_PRIMARY, vnd, fmt_int, pct


# =========================
# CHART STYLE HELPERS

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


def render_category_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Phân tích ngành hàng")

    st.markdown(
        """
        <div style="
            color: rgba(255,255,255,0.68);
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 14px;
        ">
            Trang này phân tích hiệu quả từng ngành hàng trong hệ thống thương mại điện tử:
            quy mô sản phẩm, sức bán, doanh thu ước tính, giá bán, mức giảm giá,
            coupon và chất lượng phản hồi từ khách hàng.
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

    required_cols = ["category_name", "product_id"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Thiếu cột bắt buộc: {col}")
            return

    df["category_name"] = df["category_name"].fillna("Không xác định")

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["review_count"] = df["review_count"].fillna(0)

    if "coupon_discount_amount" not in df.columns:
        df["coupon_discount_amount"] = 0

    df["coupon_discount_amount"] = pd.to_numeric(
        df["coupon_discount_amount"], errors="coerce"
    ).fillna(0)

    df["has_coupon"] = df["coupon_discount_amount"] > 0

    if "current_price" not in df.columns:
        df["current_price"] = np.nan

    if "discount_percent" not in df.columns:
        df["discount_percent"] = 0

    if "review_score" not in df.columns:
        df["review_score"] = np.nan

    if "seller_name" not in df.columns:
        df["seller_name"] = "Không xác định"

    df["estimated_revenue"] = (
        df["current_price"].fillna(0) * df["sold_quantity"].fillna(0)
    )

    price_valid_df = df[
        df["current_price"].notna() & (df["current_price"] > 0)
    ].copy()

    # =========================
    # CATEGORY SUMMARY

    category_summary = (
        df.groupby("category_name", dropna=False)
        .agg(
            product_count=("product_id", "nunique"),
            sold_quantity=("sold_quantity", "sum"),
            review_count=("review_count", "sum"),
            avg_price=("current_price", "mean"),
            median_price=("current_price", "median"),
            avg_discount=("discount_percent", "mean"),
            avg_rating=("review_score", "mean"),
            estimated_revenue=("estimated_revenue", "sum"),
            coupon_rate=("has_coupon", "mean"),
            coupon_product_count=("has_coupon", "sum"),
            seller_count=("seller_name", "nunique"),
        )
        .reset_index()
    )

    category_summary["coupon_product_count"] = category_summary["coupon_product_count"].fillna(0).astype(int)
    category_summary["coupon_rate"] = category_summary["coupon_rate"] * 100

    total_revenue = category_summary["estimated_revenue"].sum()
    total_sold = category_summary["sold_quantity"].sum()
    total_products = category_summary["product_count"].sum()

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

    category_summary["product_share"] = np.where(
        total_products > 0,
        category_summary["product_count"] / total_products * 100,
        0,
    )

    category_summary["review_per_product"] = np.where(
        category_summary["product_count"] > 0,
        category_summary["review_count"] / category_summary["product_count"],
        0,
    )

    category_summary["revenue_per_product"] = np.where(
        category_summary["product_count"] > 0,
        category_summary["estimated_revenue"] / category_summary["product_count"],
        0,
    )

    category_summary = category_summary.sort_values(
        "estimated_revenue", ascending=False
    )

    # =========================
    # KPI

    st.markdown("#### Chỉ số tổng quan ngành hàng")

    top_revenue_category = (
        category_summary.iloc[0]["category_name"]
        if not category_summary.empty
        else "—"
    )

    top_sold_category = (
        category_summary.sort_values("sold_quantity", ascending=False)
        .iloc[0]["category_name"]
        if not category_summary.empty
        else "—"
    )

    avg_coupon_rate = category_summary["coupon_rate"].mean()
    avg_category_rating = category_summary["avg_rating"].dropna().mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card(
            "Số ngành hàng",
            fmt_int(category_summary["category_name"].nunique()),
            "Đang có dữ liệu sau bộ lọc",
        )

    with k2:
        kpi_card(
            "Doanh thu cao nhất",
            clean_label(top_revenue_category, 28),
            "Ngành dẫn đầu theo doanh thu ước tính",
        )

    with k3:
        kpi_card(
            "Bán nhiều nhất",
            clean_label(top_sold_category, 28),
            "Ngành dẫn đầu theo lượt bán",
        )

    with k4:
        rating_text = (
            f"{avg_category_rating:.2f}/5"
            if not np.isnan(avg_category_rating)
            else "—"
        )
        kpi_card(
            "Rating TB theo ngành",
            rating_text,
            f"Coupon TB: {avg_coupon_rate:.1f}%",
        )

    st.markdown("---")

    # =========================
    # MT1: QUY MÔ & ĐÓNG GÓP

    render_section_title(
        "Quy mô và đóng góp của ngành hàng",
        "Xác định ngành hàng đóng góp lớn nhất về doanh thu, lượt bán và tỷ trọng trong toàn hệ thống.",
    )

    c1, c2 = st.columns(2)

    with c1:
        top_revenue = category_summary.head(10).copy()
        top_revenue["category_label"] = top_revenue["category_name"].apply(
            lambda x: wrap_label(x, 18)
        )

        fig1 = px.treemap(
            top_revenue,
            path=["category_label"],
            values="estimated_revenue",
            color="revenue_share",
            color_continuous_scale=["#0F172A", "#1D4ED8", "#38BDF8"],
            title="Cơ cấu doanh thu ước tính theo ngành hàng",
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
            category_summary
            .sort_values("estimated_revenue", ascending=False)
            .head(10)
            .copy()
        )

        pareto_df["cum_revenue_share"] = (
            pareto_df["estimated_revenue"].cumsum() / total_revenue * 100
            if total_revenue > 0
            else 0
        )

        pareto_df["category_label"] = pareto_df["category_name"].apply(
            lambda x: clean_label(x, 32)
        )
        pareto_df["revenue_label"] = pareto_df["estimated_revenue"].apply(shorten_money)
        pareto_df["cum_label"] = pareto_df["cum_revenue_share"].round(1).astype(str) + "%"

        # Đảo thứ tự để ngành doanh thu cao nhất nằm trên cùng
        pareto_df = pareto_df.sort_values("estimated_revenue", ascending=True)

        fig2 = go.Figure()

        fig2.add_trace(
            go.Bar(
                y=pareto_df["category_label"],
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
                y=pareto_df["category_label"],
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
                text="Pareto doanh thu theo ngành hàng",
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
    # MT2: HIỆU QUẢ THƯƠNG MẠI

    render_section_title(
        "Hiệu quả thương mại giữa các ngành hàng",
        "So sánh sức bán, doanh thu, rating và hiệu quả doanh thu trên mỗi sản phẩm.",
    )

    c3, c4 = st.columns(2)

    with c3:
        bubble_df = category_summary[
            (category_summary["sold_quantity"] > 0)
            & (category_summary["estimated_revenue"] > 0)
        ].copy()

        if not bubble_df.empty:
            fig3 = px.scatter(
                bubble_df,
                x="sold_quantity",
                y="estimated_revenue",
                size="product_count",
                color="avg_rating",
                hover_name="category_name",
                color_continuous_scale=["#1E1B4B", "#2563EB", "#22C55E"],
                title="Tương quan lượt bán, doanh thu và quy mô sản phẩm",
                labels={
                    "sold_quantity": "Tổng lượt bán",
                    "estimated_revenue": "Doanh thu ước tính",
                    "product_count": "Số sản phẩm",
                    "avg_rating": "Rating TB",
                },
            )

            fig3.update_traces(
                marker=dict(
                    opacity=0.78,
                    line=dict(width=1, color="rgba(255,255,255,0.45)"),
                )
            )

            fig3 = style_chart(fig3, height=460)

            fig3.update_layout(
                coloraxis_colorbar=dict(
                    title="Rating TB",
                    tickfont=dict(color=MUTED),
                    title_font=dict(color=MUTED),
                )
            )

            fig3.update_xaxes(title="Tổng lượt bán", tickformat="~s")
            fig3.update_yaxes(title="Doanh thu ước tính", tickformat="~s")

            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để vẽ biểu đồ tương quan doanh thu.")

    with c4:
        efficiency_df = category_summary.head(10).copy()
        efficiency_df["category_label"] = efficiency_df["category_name"].apply(
            lambda x: wrap_label(x, 22)
        )

        plot_df = efficiency_df.sort_values("revenue_per_product")

        fig4 = px.bar(
            plot_df,
            x="revenue_per_product",
            y="category_label",
            orientation="h",
            text=plot_df["revenue_per_product"].apply(shorten_money),
            color="revenue_per_product",
            color_continuous_scale=["#0F172A", "#0EA5E9", "#22C55E"],
            title="Hiệu quả doanh thu ước tính trên mỗi sản phẩm",
            labels={
                "revenue_per_product": "Doanh thu ước tính / sản phẩm",
                "category_label": "Ngành hàng",
            },
        )

        fig4.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            marker_line_color="rgba(255,255,255,0.18)",
            marker_line_width=1,
            hovertemplate="<b>%{y}</b><br>Doanh thu/SP: %{x:,.0f} ₫<extra></extra>",
        )

        fig4 = style_chart(fig4, height=460)
        fig4.update_layout(showlegend=False, coloraxis_showscale=False)
        fig4.update_xaxes(tickformat="~s")

        st.plotly_chart(fig4, use_container_width=True)

    # =========================
    # MT3: GIÁ & DISCOUNT

    render_section_title(
        "Chiến lược giá và khuyến mãi theo ngành hàng",
        "Phân tích phân bố giá bán và tác động của từng nhóm discount đến lượt bán.",
    )

    c5, c6 = st.columns(2)

    with c5:
        top_price_categories = (
            category_summary
            .sort_values("product_count", ascending=False)
            .head(8)["category_name"]
            .tolist()
        )

        box_df = price_valid_df[
            price_valid_df["category_name"].isin(top_price_categories)
        ].copy()

        if not box_df.empty:
            upper_price = box_df["current_price"].quantile(0.97)
            box_df = box_df[box_df["current_price"] <= upper_price]

            box_df["category_label"] = box_df["category_name"].apply(
                lambda x: clean_label(x, 32)
            )

            fig5 = px.box(
                box_df,
                x="current_price",
                y="category_label",
                color="category_label",
                points=False,
                title="Phân bố giá bán theo ngành hàng phổ biến",
                labels={
                    "category_label": "Ngành hàng",
                    "current_price": "Giá hiện tại",
                },
            )

            fig5.update_traces(
                marker=dict(opacity=0.75),
                line=dict(width=1.4),
                hovertemplate="<b>%{y}</b><br>Giá: %{x:,.0f} ₫<extra></extra>",
            )

            fig5 = style_chart(fig5, height=470)
            fig5.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=70, b=70),
            )
            fig5.update_xaxes(tickformat="~s")

            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu giá để hiển thị.")

    with c6:
        discount_df = df.copy()

        discount_df["discount_group"] = pd.cut(
            discount_df["discount_percent"].fillna(0),
            bins=[-1, 0, 10, 20, 30, 50, 100],
            labels=[
                "0%",
                "1–10%",
                "11–20%",
                "21–30%",
                "31–50%",
                ">50%",
            ],
        )

        top_discount_categories = (
            category_summary.sort_values("sold_quantity", ascending=False)
            .head(10)["category_name"]
            .tolist()
        )

        heat_df = discount_df[
            discount_df["category_name"].isin(top_discount_categories)
        ].copy()

        heat_summary = (
            heat_df.groupby(["category_name", "discount_group"], observed=False)
            .agg(sold_quantity=("sold_quantity", "sum"))
            .reset_index()
        )

        if not heat_summary.empty:
            heat_summary["category_label"] = heat_summary["category_name"].apply(
                lambda x: wrap_label(x, 22)
            )

            fig6 = px.density_heatmap(
                heat_summary,
                x="discount_group",
                y="category_label",
                z="sold_quantity",
                color_continuous_scale=["#111827", "#F59E0B", "#F97316", "#EF4444"],
                title="Heatmap lượt bán theo nhóm discount và ngành hàng",
                labels={
                    "discount_group": "Nhóm giảm giá",
                    "category_label": "Ngành hàng",
                    "sold_quantity": "Lượt bán",
                },
            )

            fig6.update_traces(
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Nhóm giảm giá: %{x}<br>"
                    "Lượt bán: %{z:,.0f}<extra></extra>"
                )
            )

            fig6 = style_chart(fig6, height=470)

            fig6.update_layout(
                coloraxis_colorbar=dict(
                    title="Lượt bán",
                    tickfont=dict(color=MUTED),
                    title_font=dict(color=MUTED),
                )
            )

            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu discount để hiển thị.")

    # =========================
    # MT4: COUPON

    render_section_title(
        "Mức độ sử dụng coupon theo ngành hàng",
        "Xem ngành hàng nào đang dùng coupon nhiều và coupon có đi kèm sức bán tốt hay không.",
    )

    c7, c8 = st.columns(2)

    with c7:
        coupon_df = (
            category_summary
            .sort_values("coupon_product_count", ascending=False)
            .head(10)
            .copy()
        )

        coupon_df["category_label"] = coupon_df["category_name"].apply(
            lambda x: clean_label(x, 34)
        )
        coupon_df["coupon_count_label"] = (
            coupon_df["coupon_product_count"].astype(int).astype(str) + " SP"
        )
        coupon_df["coupon_rate_label"] = (
            coupon_df["coupon_rate"].round(1).astype(str) + "%"
        )

        plot_coupon_df = coupon_df.sort_values("coupon_product_count")

        fig7 = px.bar(
            plot_coupon_df,
            x="coupon_product_count",
            y="category_label",
            orientation="h",
            text="coupon_count_label",
            color="coupon_rate",
            color_continuous_scale=["#1E1B4B", "#7C3AED", "#C4B5FD"],
            title="Top ngành hàng theo số sản phẩm có coupon",
            labels={
                "coupon_product_count": "Số sản phẩm có coupon",
                "category_label": "Ngành hàng",
                "coupon_rate": "Tỷ lệ coupon (%)",
            },
            custom_data=[
                "product_count",
                "coupon_rate",
                "sold_quantity",
                "estimated_revenue",
            ],
        )

        fig7.update_traces(
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
            marker_line_color="rgba(255,255,255,0.20)",
            marker_line_width=1,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Sản phẩm có coupon: %{x:,.0f}<br>"
                "Tổng sản phẩm: %{customdata[0]:,.0f}<br>"
                "Tỷ lệ coupon: %{customdata[1]:.1f}%<br>"
                "Lượt bán: %{customdata[2]:,.0f}<br>"
                "Doanh thu ước tính: %{customdata[3]:,.0f} ₫"
                "<extra></extra>"
            ),
        )

        fig7 = style_chart(fig7, height=450)

        fig7.update_layout(
            showlegend=False,
            coloraxis_colorbar=dict(
                title="Tỷ lệ coupon",
                tickfont=dict(color=MUTED),
                title_font=dict(color=MUTED),
            ),
            margin=dict(l=20, r=60, t=70, b=70),
        )

        max_coupon_count = coupon_df["coupon_product_count"].max()
        fig7.update_xaxes(
            title="Số sản phẩm có coupon",
            range=[0, max_coupon_count * 1.18 if max_coupon_count > 0 else 1],
        )

        st.plotly_chart(fig7, use_container_width=True)

    with c8:
        coupon_effect_df = category_summary[
            (category_summary["product_count"] > 0)
            & (category_summary["sold_quantity"] > 0)
        ].copy()

        if not coupon_effect_df.empty:
            fig8 = px.scatter(
                coupon_effect_df,
                x="coupon_rate",
                y="sold_quantity",
                size="estimated_revenue",
                color="avg_discount",
                hover_name="category_name",
                color_continuous_scale=["#1E1B4B", "#2563EB", "#F59E0B", "#EF4444"],
                title="Coupon, discount và sức bán theo ngành hàng",
                labels={
                    "coupon_rate": "Tỷ lệ coupon (%)",
                    "sold_quantity": "Tổng lượt bán",
                    "estimated_revenue": "Doanh thu ước tính",
                    "avg_discount": "Discount TB (%)",
                },
            )

            fig8.update_traces(
                marker=dict(
                    opacity=0.78,
                    line=dict(width=1, color="rgba(255,255,255,0.45)"),
                )
            )

            fig8 = style_chart(fig8, height=450)

            fig8.update_layout(
                coloraxis_colorbar=dict(
                    title="Discount TB",
                    tickfont=dict(color=MUTED),
                    title_font=dict(color=MUTED),
                )
            )

            fig8.update_xaxes(title="Tỷ lệ coupon (%)")
            fig8.update_yaxes(title="Tổng lượt bán", tickformat="~s")

            st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu coupon để hiển thị.")

    # =========================
    # MT5: RATING & RỦI RO

    render_section_title(
        "Chất lượng phản hồi và nhóm ngành cần chú ý",
        "Nhận diện ngành hàng doanh thu cao nhưng rating thấp, hoặc có nhiều review nhưng chất lượng chưa tốt.",
    )

    c9, c10 = st.columns(2)

    with c9:
        rating_df = df.dropna(subset=["review_score"]).copy()

        rating_df["rating_group"] = pd.cut(
            rating_df["review_score"],
            bins=[-0.01, 3, 4, 4.5, 5],
            labels=[
                "≤ 3 sao",
                "3–4 sao",
                "4–4.5 sao",
                "4.5–5 sao",
            ],
            include_lowest=True,
        )

        top_rating_categories = (
            category_summary.sort_values("review_count", ascending=False)
            .head(10)["category_name"]
            .tolist()
        )

        rating_df = rating_df[
            rating_df["category_name"].isin(top_rating_categories)
        ].copy()

        rating_summary = (
            rating_df.groupby(["category_name", "rating_group"], observed=False)
            .agg(product_count=("product_id", "nunique"))
            .reset_index()
        )

        if not rating_summary.empty:
            rating_summary["category_label"] = rating_summary["category_name"].apply(
                lambda x: wrap_label(x, 14)
            )

            fig9 = px.bar(
                rating_summary,
                x="category_label",
                y="product_count",
                color="rating_group",
                title="Cơ cấu nhóm rating theo ngành hàng có nhiều review",
                color_discrete_map={
                    "≤ 3 sao": RED,
                    "3–4 sao": ORANGE,
                    "4–4.5 sao": CYAN,
                    "4.5–5 sao": GREEN,
                },
                labels={
                    "category_label": "Ngành hàng",
                    "product_count": "Số sản phẩm",
                    "rating_group": "Nhóm rating",
                },
            )

            fig9.update_traces(
                marker_line_color="rgba(255,255,255,0.16)",
                marker_line_width=0.8,
                hovertemplate="<b>%{x}</b><br>Số sản phẩm: %{y:,.0f}<extra></extra>",
            )

            fig9 = style_chart(fig9, height=470, legend_top=True)

            fig9.update_layout(
                barmode="stack",
                margin=dict(l=20, r=20, t=80, b=130),
            )

            st.plotly_chart(fig9, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu rating để hiển thị.")

    with c10:
        risk_df = category_summary.copy()

        revenue_threshold = risk_df["estimated_revenue"].quantile(0.70)
        rating_threshold = 4.0

        risk_df["risk_group"] = np.select(
            [
                (risk_df["estimated_revenue"] >= revenue_threshold)
                & (risk_df["avg_rating"] < rating_threshold),
                (risk_df["estimated_revenue"] >= revenue_threshold)
                & (risk_df["avg_rating"] >= rating_threshold),
                (risk_df["estimated_revenue"] < revenue_threshold)
                & (risk_df["avg_rating"] >= rating_threshold),
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
            & (risk_df["avg_rating"].notna())
        ].copy()

        if not risk_plot_df.empty:
            fig10 = px.scatter(
                risk_plot_df,
                x="avg_rating",
                y="estimated_revenue",
                size="review_count",
                color="risk_group",
                hover_name="category_name",
                color_discrete_map={
                    "Doanh thu cao - Rating thấp": RED,
                    "Doanh thu cao - Rating tốt": GREEN,
                    "Doanh thu thấp - Rating tốt": CYAN,
                    "Doanh thu thấp - Rating thấp": "rgba(255,255,255,0.45)",
                },
                title="Ma trận doanh thu và chất lượng đánh giá",
                labels={
                    "avg_rating": "Rating TB",
                    "estimated_revenue": "Doanh thu ước tính",
                    "review_count": "Số review",
                    "risk_group": "Nhóm ngành",
                },
            )

            fig10.update_traces(
                marker=dict(
                    opacity=0.82,
                    line=dict(width=1, color="rgba(255,255,255,0.5)"),
                )
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

            fig10 = style_chart(fig10, height=470)

            fig10.update_layout(
                margin=dict(l=20, r=20, t=70, b=110),
            )

            fig10.update_xaxes(range=[0, 5.1])
            fig10.update_yaxes(tickformat="~s")

            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để hiển thị ma trận rủi ro.")

    # =========================
    # TABLE

    render_section_title(
        "Bảng tổng hợp hiệu quả ngành hàng",
        "Bảng số liệu chi tiết để đối chiếu các biểu đồ phía trên.",
    )

    table_df = category_summary.copy()

    table_df["avg_price"] = table_df["avg_price"].round(0)
    table_df["median_price"] = table_df["median_price"].round(0)
    table_df["avg_discount"] = table_df["avg_discount"].round(2)
    table_df["avg_rating"] = table_df["avg_rating"].round(2)
    table_df["estimated_revenue"] = table_df["estimated_revenue"].round(0)
    table_df["revenue_share"] = table_df["revenue_share"].round(2)
    table_df["coupon_rate"] = table_df["coupon_rate"].round(2)
    table_df["coupon_product_count"] = table_df["coupon_product_count"].astype(int)
    table_df["review_per_product"] = table_df["review_per_product"].round(2)
    table_df["revenue_per_product"] = table_df["revenue_per_product"].round(0)

    table_df = table_df.rename(
        columns={
            "category_name": "Ngành hàng",
            "product_count": "Số sản phẩm",
            "coupon_product_count": "Số SP có coupon",
            "seller_count": "Số người bán",
            "sold_quantity": "Lượt bán",
            "review_count": "Số review",
            "avg_price": "Giá TB",
            "median_price": "Giá trung vị",
            "avg_discount": "Discount TB (%)",
            "avg_rating": "Rating TB",
            "estimated_revenue": "Doanh thu ước tính",
            "revenue_share": "Tỷ trọng doanh thu (%)",
            "coupon_rate": "Tỷ lệ coupon (%)",
            "review_per_product": "Review / sản phẩm",
            "revenue_per_product": "Doanh thu / sản phẩm",
        }
    )

    st.dataframe(
        table_df[
            [
                "Ngành hàng",
                "Số sản phẩm",
                "Số SP có coupon",
                "Số người bán",
                "Lượt bán",
                "Số review",
                "Giá TB",
                "Giá trung vị",
                "Discount TB (%)",
                "Tỷ lệ coupon (%)",
                "Rating TB",
                "Doanh thu ước tính",
                "Tỷ trọng doanh thu (%)",
                "Review / sản phẩm",
                "Doanh thu / sản phẩm",
            ]
        ],
        use_container_width=True,
        height=420,
    )
