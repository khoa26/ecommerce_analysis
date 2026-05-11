from __future__ import annotations
from textwrap import dedent

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
PURPLE = "#A78BFA"


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
            review_count=("review_count_real", "sum"),
            estimated_revenue=("estimated_revenue", "sum"),
            avg_price=("current_price", "mean"),
            median_price=("current_price", "median"),
            avg_discount=("discount_percent", "mean"),
            coupon_rate=("has_coupon", "mean"),
            discount_rate=("has_discount", "mean"),
            product_rating=("product_rating", "mean"),
            review_rating=("review_rating", "mean"),
            seller_rating=("seller_rating_clean", "mean"),
        )
        .reset_index()
    )

    cat["category_label"] = cat["category_name"].apply(lambda x: clean_label(x, 30))

    cat["revenue_per_product"] = np.where(
        cat["product_count"] > 0,
        cat["estimated_revenue"] / cat["product_count"],
        0,
    )

    cat["sold_per_product"] = np.where(
        cat["product_count"] > 0,
        cat["sold_quantity"] / cat["product_count"],
        0,
    )

    return cat


def render_category_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Phân tích ngành hàng")

    st.markdown(
        dedent(
            """
            <div style="
                color:rgba(255,255,255,0.68);
                font-size:0.95rem;
                line-height:1.6;
                margin-bottom:14px;
            ">

            </div>
            """
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
        "review_count_real",
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

    numeric_cols = [
        "sold_quantity",
        "review_count_real",
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
    df["review_count_real"] = df["review_count_real"].fillna(0)
    df["current_price"] = df["current_price"].fillna(0)
    df["estimated_revenue"] = df["estimated_revenue"].fillna(0)
    df["discount_percent"] = df["discount_percent"].fillna(0)
    df["has_coupon"] = df["has_coupon"].fillna(False).astype(bool)
    df["has_discount"] = df["has_discount"].fillna(False).astype(bool)
    df["category_name"] = df["category_name"].fillna("Không xác định")

    cat = build_category_summary(df)

    if cat.empty:
        st.warning("Không đủ dữ liệu ngành hàng để phân tích.")
        return

    # =============================
    # KPI
    # =============================
    best_revenue_cat = cat.sort_values("estimated_revenue", ascending=False).iloc[0]
    best_sold_cat = cat.sort_values("sold_quantity", ascending=False).iloc[0]

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi(
            "Số ngành hàng",
            fmt_int(cat["category_name"].nunique()),

        )

    with k2:
        kpi(
            "Doanh thu ước tính",
            money_short(cat["estimated_revenue"].sum()),
            "Tổng doanh thu theo ngành",
        )

    with k3:
        kpi(
            "Ngành doanh thu cao nhất",
            best_revenue_cat["category_label"],
            money_short(best_revenue_cat["estimated_revenue"]),
        )

    with k4:
        kpi(
            "Ngành bán nhiều nhất",
            best_sold_cat["category_label"],
            fmt_int(best_sold_cat["sold_quantity"]) + " lượt bán",
        )



    # =============================
    # CHART 1: TOP CATEGORY REVENUE
    # =============================
    section(
        "1. Top ngành hàng theo doanh thu ước tính",
        "Mục tiêu: xác định các ngành hàng đóng góp nhiều doanh thu nhất.",
    )

    top_rev = (
        cat.sort_values("estimated_revenue", ascending=False)
        .head(12)
        .sort_values("estimated_revenue")
    )

    fig = go.Figure()

    fig.add_bar(
        x=top_rev["estimated_revenue"],
        y=top_rev["category_label"],
        orientation="h",
        marker_color=BLUE,
        text=top_rev["estimated_revenue"].map(money_short),
        textposition="outside",
        customdata=np.stack(
            [
                top_rev["sold_quantity"],
                top_rev["product_count"],
                top_rev["seller_count"],
                top_rev["review_rating"].round(2),
            ],
            axis=-1,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Doanh thu: %{x:,.0f} đ"
            "<br>Lượt bán: %{customdata[0]:,.0f}"
            "<br>Số sản phẩm: %{customdata[1]:,.0f}"
            "<br>Số người bán: %{customdata[2]:,.0f}"
            "<br>Review rating: %{customdata[3]:.2f}/5"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        title="Top 12 ngành hàng đóng góp doanh thu",
        showlegend=False,
    )
    fig.update_xaxes(title="Doanh thu ước tính", tickformat="~s")
    fig.update_yaxes(title="")

    plot_chart(fig, height=520)

    # =============================
    # CHART 2: BUBBLE CATEGORY MATRIX
    # =============================
    section(
        "2. Ma trận ngành hàng: doanh thu, lượt bán và chất lượng",
        "Bong bóng càng lớn nghĩa là ngành có nhiều sản phẩm. Màu thể hiện Review rating trung bình.",
    )

    bubble_df = cat[
        (cat["estimated_revenue"] > 0)
        & (cat["sold_quantity"] > 0)
    ].copy()

    bubble_df = bubble_df.sort_values("estimated_revenue", ascending=False).head(30)

    if bubble_df.empty:
        st.info("Không đủ dữ liệu để hiển thị ma trận.")
    else:
        max_size = max(bubble_df["product_count"].max(), 1)

        fig = go.Figure()

        fig.add_scatter(
            x=bubble_df["sold_quantity"],
            y=bubble_df["estimated_revenue"],
            mode="markers+text",
            text=bubble_df["category_label"].where(
                bubble_df["estimated_revenue"].rank(ascending=False) <= 6,
                "",
            ),
            textposition="top center",
            marker=dict(
                size=14 + 46 * np.sqrt(bubble_df["product_count"] / max_size),
                color=bubble_df["review_rating"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Review<br>rating"),
                opacity=0.78,
                line=dict(width=1, color="rgba(255,255,255,0.78)"),
            ),
            customdata=np.stack(
                [
                    bubble_df["category_label"],
                    bubble_df["product_count"],
                    bubble_df["seller_count"],
                    bubble_df["review_rating"].round(2),
                    bubble_df["coupon_rate"].map(lambda x: pct(x * 100)),
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Lượt bán: %{x:,.0f}"
                "<br>Doanh thu: %{y:,.0f} đ"
                "<br>Sản phẩm: %{customdata[1]:,.0f}"
                "<br>Người bán: %{customdata[2]:,.0f}"
                "<br>Review rating: %{customdata[3]:.2f}/5"
                "<br>Coupon rate: %{customdata[4]}"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            title="Lượt bán vs doanh thu theo ngành hàng",
            showlegend=False,
        )
        fig.update_xaxes(title="Tổng lượt bán", tickformat="~s")
        fig.update_yaxes(title="Doanh thu ước tính", tickformat="~s")

        plot_chart(fig, height=540, hovermode="closest")

        

        # =============================
        # CHART 3: RADAR PERFORMANCE PROFILE
        # =============================
        section(
            "3. Hồ sơ hiệu suất của nhóm ngành hàng chủ lực",
            "Mục tiêu: so sánh các ngành hàng top doanh thu theo nhiều tiêu chí: doanh thu, lượt bán, độ phủ sản phẩm, chất lượng review và mức độ dùng coupon.",
        )

        radar_df = cat.sort_values("estimated_revenue", ascending=False).head(5).copy()

        if radar_df.empty:
            st.info("Không đủ dữ liệu để vẽ biểu đồ radar.")
        else:
            radar_metrics = {
                "Doanh thu": "estimated_revenue",
                "Lượt bán": "sold_quantity",
                "Số sản phẩm": "product_count",
                "Review rating": "review_rating",
                "Coupon rate": "coupon_rate",
            }

            # Chuẩn hóa các chỉ số về thang 0–100 để so sánh được trên cùng radar
            for label, col in radar_metrics.items():
                max_value = radar_df[col].max()

                if pd.isna(max_value) or max_value == 0:
                    radar_df[label] = 0
                else:
                    radar_df[label] = radar_df[col] / max_value * 100

            categories = list(radar_metrics.keys())

            fig = go.Figure()

            for _, row in radar_df.iterrows():
                values = [row[c] for c in categories]

                # Đóng vòng radar
                fig.add_trace(
                    go.Scatterpolar(
                        r=values + [values[0]],
                        theta=categories + [categories[0]],
                        fill="toself",
                        name=row["category_label"],
                        customdata=[
                            row["estimated_revenue"],
                            row["sold_quantity"],
                            row["product_count"],
                            row["review_rating"],
                            row["coupon_rate"] * 100,
                        ],
                        hovertemplate=(
                            "<b>%{fullData.name}</b><br>"
                            "Chỉ số chuẩn hóa: %{r:.1f}/100"
                            "<extra></extra>"
                        ),
                    )
                )

            fig.update_layout(
                title="Radar hiệu suất của top 5 ngành hàng theo doanh thu",
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        tickfont=dict(size=10),
                        gridcolor="rgba(255,255,255,0.12)",
                    ),
                    angularaxis=dict(
                        tickfont=dict(size=11),
                        gridcolor="rgba(255,255,255,0.12)",
                    ),
                    bgcolor="rgba(255,255,255,0.025)",
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.12,
                    xanchor="center",
                    x=0.5,
                ),
                margin=dict(l=40, r=40, t=80, b=110),
            )

            plot_chart(fig, height=560, hovermode="closest")

            

        # =============================
        # CHART 4: TREEMAP PROMOTION DEPENDENCY
        # =============================
        section(
            "4. Mức độ phụ thuộc khuyến mãi của ngành hàng",
            "Mục tiêu: xác định ngành hàng nào đang tạo doanh thu lớn và đồng thời phụ thuộc nhiều vào coupon.",
        )

        promo_tree = (
            cat[cat["estimated_revenue"] > 0]
            .sort_values(["estimated_revenue", "coupon_rate"], ascending=[False, False])
            .head(15)
            .copy()
        )

        if promo_tree.empty:
            st.info("Không đủ dữ liệu để vẽ treemap khuyến mãi.")
        else:
            promo_tree["coupon_rate_pct"] = promo_tree["coupon_rate"] * 100
            promo_tree["avg_discount_pct"] = promo_tree["avg_discount"].fillna(0)
            promo_tree["review_rating_text"] = promo_tree["review_rating"].apply(
                lambda x: f"{x:.2f}/5" if pd.notna(x) else "Chưa có review"
            )
            promo_tree["revenue_text"] = promo_tree["estimated_revenue"].map(money_short)

            fig = go.Figure(
                go.Treemap(
                    labels=promo_tree["category_label"],
                    parents=[""] * len(promo_tree),
                    values=promo_tree["estimated_revenue"],
                    marker=dict(
                        colors=promo_tree["coupon_rate_pct"],
                        colorscale="YlOrRd",
                        colorbar=dict(title="Coupon<br>rate (%)"),
                        line=dict(width=1, color="rgba(255,255,255,0.25)")
                    ),
                    customdata=np.stack(
                        [
                            promo_tree["revenue_text"],
                            promo_tree["sold_quantity"],
                            promo_tree["coupon_rate_pct"].round(1),
                            promo_tree["avg_discount_pct"].round(1),
                            promo_tree["review_rating_text"],
                        ],
                        axis=-1,
                    ),
                    texttemplate="<b>%{label}</b><br>%{customdata[0]}",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Doanh thu: %{customdata[0]}"
                        "<br>Lượt bán: %{customdata[1]:,.0f}"
                        "<br>Coupon rate: %{customdata[2]}%"
                        "<br>Discount TB: %{customdata[3]}%"
                        "<br>Review rating: %{customdata[4]}"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(
                title="Treemap doanh thu ngành hàng, tô màu theo Coupon rate",
                margin=dict(l=20, r=20, t=70, b=20),
            )

            plot_chart(fig, height=560, hovermode="closest")

           
    # =============================
    # CHART 5: HEATMAP
    # =============================
    section(
        "5. Heatmap: mức giá × nhóm điểm đánh giá review",
        "Mục tiêu: hiểu rõ hơn về sự phân bố sản phẩm theo mức giá và chất lượng review, từ đó xác định các phân khúc thị trường tiềm năng hoặc đang bão hòa.",
    )

    heat_df = df[
        (df["current_price"] > 0)
        & (df["review_rating"].notna())
    ].copy()

    if heat_df.empty:
        st.info("Không đủ dữ liệu giá và review rating để vẽ heatmap.")
    else:
        price_bins = [0, 100_000, 300_000, 700_000, 1_500_000, np.inf]
        price_labels = ["≤100K", "100–300K", "300–700K", "700K–1.5M", ">1.5M"]

        rating_bins = [0, 2, 3, 4, 4.5, 5]
        rating_labels = ["≤2", "2–3", "3–4", "4–4.5", "4.5–5"]

        heat_df["price_group"] = pd.cut(
            heat_df["current_price"],
            bins=price_bins,
            labels=price_labels,
            include_lowest=True,
        )

        heat_df["rating_group"] = pd.cut(
            heat_df["review_rating"],
            bins=rating_bins,
            labels=rating_labels,
            include_lowest=True,
        )

        pivot = heat_df.pivot_table(
            index="rating_group",
            columns="price_group",
            values="product_id",
            aggfunc="nunique",
            fill_value=0,
            observed=False,
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=[str(x) for x in pivot.columns],
                y=[str(y) for y in pivot.index],
                colorscale="Blues",
                text=pivot.values,
                texttemplate="%{text:,.0f}",
                hovertemplate=(
                    "Mức giá: %{x}<br>"
                    "Nhóm Review rating: %{y}<br>"
                    "Số sản phẩm: %{z:,.0f}"
                    "<extra></extra>"
                ),
                colorbar=dict(title="Số SP"),
            )
        )

        fig.update_layout(
            title="Số sản phẩm theo mức giá và nhóm điểm đánh giá review",
            showlegend=False,
        )
        fig.update_xaxes(title="Mức giá")
        fig.update_yaxes(title="Nhóm Review rating")

        plot_chart(fig, height=460, hovermode="closest")

        

    # =============================
    # TABLE
    # =============================
    section(
        "Bảng chi tiết ngành hàng",
        "Dùng bảng này để kiểm chứng số liệu biểu đồ và lấy số đưa vào báo cáo.",
    )

    table = cat.sort_values("estimated_revenue", ascending=False).copy()

    table["Doanh thu"] = table["estimated_revenue"].apply(money_short)
    table["Lượt bán"] = table["sold_quantity"].apply(fmt_int)
    table["Số sản phẩm"] = table["product_count"].apply(fmt_int)
    table["Số người bán"] = table["seller_count"].apply(fmt_int)
    table["Coupon rate"] = table["coupon_rate"].apply(lambda x: pct(x * 100))
    table["Discount TB"] = table["avg_discount"].map(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    table["Product rating"] = table["product_rating"].round(2)
    table["Review rating"] = table["review_rating"].round(2)
    table["Seller rating"] = table["seller_rating"].round(2)

    st.dataframe(
        table[
            [
                "category_name",
                "Số sản phẩm",
                "Số người bán",
                "Lượt bán",
                "Doanh thu",
                "Coupon rate",
                "Discount TB",
                "Product rating",
                "Review rating",
                "Seller rating",
            ]
        ].rename(columns={"category_name": "Ngành hàng"}),
        use_container_width=True,
        hide_index=True,
    )