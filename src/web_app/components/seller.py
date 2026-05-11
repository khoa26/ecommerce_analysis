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
RED = "#F87171"


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




def build_seller_summary(df: pd.DataFrame) -> pd.DataFrame:
    seller = (
        df.groupby("seller_name", dropna=False)
        .agg(
            product_count=("product_id", "nunique"),
            category_count=("category_name", "nunique"),
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
            bad_review_count=("bad_review_count", "sum"),
        )
        .reset_index()
    )

    seller["seller_label"] = seller["seller_name"].apply(lambda x: clean_label(x, 32))

    seller["revenue_per_product"] = np.where(
        seller["product_count"] > 0,
        seller["estimated_revenue"] / seller["product_count"],
        0,
    )

    seller["sold_per_product"] = np.where(
        seller["product_count"] > 0,
        seller["sold_quantity"] / seller["product_count"],
        0,
    )

    seller["bad_review_rate"] = np.where(
        seller["review_count"] > 0,
        seller["bad_review_count"] / seller["review_count"],
        0,
    )

    return seller


def render_seller_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Phân tích người bán")

    st.markdown(
        dedent(
            """
            <div style="
                color:rgba(255,255,255,0.68);
                font-size:0.95rem;
                line-height:1.6;
                margin-bottom:14px;
            ">
                Trang này tập trung vào hiệu quả người bán: ai tạo doanh thu cao, ai bán nhiều,
                rating của seller có tương thích với review thực tế không và coupon/discount có hỗ trợ sức bán không.
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
        "seller_name",
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
        "bad_review_count",
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
        "bad_review_count",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["review_count_real"] = df["review_count_real"].fillna(0)
    df["current_price"] = df["current_price"].fillna(0)
    df["discount_percent"] = df["discount_percent"].fillna(0)
    df["estimated_revenue"] = df["estimated_revenue"].fillna(0)
    df["bad_review_count"] = df["bad_review_count"].fillna(0)
    df["has_coupon"] = df["has_coupon"].fillna(False).astype(bool)
    df["has_discount"] = df["has_discount"].fillna(False).astype(bool)
    df["seller_name"] = df["seller_name"].fillna("Không xác định")
    df["category_name"] = df["category_name"].fillna("Không xác định")

    seller = build_seller_summary(df)

    if seller.empty:
        st.warning("Không đủ dữ liệu người bán để phân tích.")
        return

    # =============================
    # KPI
    # =============================
    best_revenue_seller = seller.sort_values("estimated_revenue", ascending=False).iloc[0]
    best_sold_seller = seller.sort_values("sold_quantity", ascending=False).iloc[0]

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi(
            "Số người bán",
            fmt_int(seller["seller_name"].nunique()),
            "Người bán sau bộ lọc",
        )

    with k2:
        kpi(
            "Doanh thu ước tính",
            money_short(seller["estimated_revenue"].sum()),
            "Tổng doanh thu từ người bán",
        )

    with k3:
        kpi(
            "Seller doanh thu cao nhất",
            best_revenue_seller["seller_label"],
            money_short(best_revenue_seller["estimated_revenue"]),
        )

    with k4:
        kpi(
            "Seller bán nhiều nhất",
            best_sold_seller["seller_label"],
            fmt_int(best_sold_seller["sold_quantity"]) + " lượt bán",
        )

    r1, r2, r3 = st.columns(3)

    with r1:
        kpi(
            "Seller rating TB",
            f"{seller['seller_rating'].dropna().mean():.2f}/5",
            "Điểm seller_rating",
        )

    with r2:
        kpi(
            "Review rating TB",
            f"{seller['review_rating'].dropna().mean():.2f}/5",
            "Điểm rating_score từ review",
        )

    with r3:
        kpi(
            "Tỷ lệ bad review",
            pct(seller["bad_review_rate"].mean() * 100),
            "Review có điểm ≤ 2 sao",
        )


        # =============================
    # CHART 1: PARETO SELLER REVENUE
    # =============================
    section(
        "1. Mức độ tập trung doanh thu theo người bán",
        "Mục tiêu: xác định doanh thu hệ thống có đang phụ thuộc vào một vài seller chủ lực hay không.",
    )

    pareto_df = (
        seller[seller["estimated_revenue"] > 0]
        .sort_values("estimated_revenue", ascending=False)
        .head(12)
        .copy()
    )

    if pareto_df.empty:
        st.info("Không đủ dữ liệu để vẽ biểu đồ Pareto doanh thu seller.")
    else:
        total_revenue_all = seller["estimated_revenue"].sum()

        pareto_df["revenue_share"] = np.where(
            total_revenue_all > 0,
            pareto_df["estimated_revenue"] / total_revenue_all * 100,
            0,
        )

        pareto_df["cum_share"] = pareto_df["revenue_share"].cumsum()

        fig = go.Figure()

        fig.add_bar(
            x=pareto_df["seller_label"],
            y=pareto_df["estimated_revenue"],
            name="Doanh thu ước tính",
            marker_color=BLUE,
            text=pareto_df["estimated_revenue"].map(money_short),
            textposition="outside",
            customdata=np.stack(
                [
                    pareto_df["sold_quantity"],
                    pareto_df["product_count"],
                    pareto_df["category_count"],
                    pareto_df["revenue_share"].round(1),
                    pareto_df["cum_share"].round(1),
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Doanh thu: %{y:,.0f} đ"
                "<br>Lượt bán: %{customdata[0]:,.0f}"
                "<br>Số sản phẩm: %{customdata[1]:,.0f}"
                "<br>Số ngành: %{customdata[2]:,.0f}"
                "<br>Tỷ trọng doanh thu: %{customdata[3]:.1f}%"
                "<br>Tỷ trọng lũy kế: %{customdata[4]:.1f}%"
                "<extra></extra>"
            ),
        )

        fig.add_scatter(
            x=pareto_df["seller_label"],
            y=pareto_df["cum_share"],
            name="Tỷ trọng lũy kế (%)",
            mode="lines+markers+text",
            text=pareto_df["cum_share"].map(lambda x: f"{x:.0f}%"),
            textposition="top center",
            yaxis="y2",
            marker=dict(
                size=9,
                color=ORANGE,
                line=dict(width=1, color="white"),
            ),
            line=dict(width=3, color=ORANGE),
            hovertemplate="<b>%{x}</b><br>Tỷ trọng lũy kế: %{y:.1f}%<extra></extra>",
        )

        fig.update_layout(
            title="Pareto doanh thu theo người bán",
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

        fig.update_xaxes(title="Người bán", tickangle=-25)

        plot_chart(fig, height=520, hovermode="closest", legend_top=True)

       

    # =============================
    # CHART 2: SELLER POSITIONING MATRIX
    # =============================
    section(
        "2. Ma trận vị thế người bán: doanh thu, lượt bán và chất lượng",
        "Mục tiêu: phân nhóm seller theo quy mô bán hàng, doanh thu tạo ra và chất lượng review thực tế.",
    )

    bubble_df = seller[
        (seller["estimated_revenue"] > 0)
        & (seller["sold_quantity"] > 0)
    ].copy()

    bubble_df = bubble_df.sort_values("estimated_revenue", ascending=False).head(35)

    if bubble_df.empty:
        st.info("Không đủ dữ liệu để vẽ ma trận người bán.")
    else:
        max_size = max(bubble_df["product_count"].max(), 1)

        bubble_df["review_rating_text"] = bubble_df["review_rating"].apply(
            lambda x: f"{x:.2f}/5" if pd.notna(x) else "Chưa có review"
        )

        fig = go.Figure()

        fig.add_scatter(
            x=bubble_df["sold_quantity"],
            y=bubble_df["estimated_revenue"],
            mode="markers+text",
            text=bubble_df["seller_label"].where(
                bubble_df["estimated_revenue"].rank(ascending=False) <= 7,
                "",
            ),
            textposition="top center",
            marker=dict(
                size=12 + 44 * np.sqrt(bubble_df["product_count"] / max_size),
                color=bubble_df["review_rating"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Review<br>rating"),
                opacity=0.78,
                line=dict(width=1, color="rgba(255,255,255,0.75)"),
            ),
            customdata=np.stack(
                [
                    bubble_df["seller_label"],
                    bubble_df["product_count"],
                    bubble_df["category_count"],
                    bubble_df["seller_rating"].round(2),
                    bubble_df["review_rating_text"],
                    bubble_df["bad_review_rate"].map(lambda x: pct(x * 100)),
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Lượt bán: %{x:,.0f}"
                "<br>Doanh thu: %{y:,.0f} đ"
                "<br>Sản phẩm: %{customdata[1]:,.0f}"
                "<br>Số ngành: %{customdata[2]:,.0f}"
                "<br>Seller rating: %{customdata[3]:.2f}/5"
                "<br>Review rating: %{customdata[4]}"
                "<br>Bad review rate: %{customdata[5]}"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            title="Doanh thu vs lượt bán theo người bán",
            showlegend=False,
        )
        fig.update_xaxes(title="Tổng lượt bán", tickformat="~s")
        fig.update_yaxes(title="Doanh thu ước tính", tickformat="~s")

        plot_chart(fig, height=540, hovermode="closest")

      

    # =============================
    # CHART 3: SELLER PRODUCT EFFICIENCY
    # =============================
    section(
        "3. Hiệu suất doanh thu trên mỗi sản phẩm của seller",
        "Mục tiêu: tìm seller có danh mục sản phẩm gọn nhưng tạo doanh thu tốt, thay vì chỉ nhìn tổng doanh thu.",
    )

    eff_df = (
        seller[
            (seller["product_count"] > 0)
            & (seller["estimated_revenue"] > 0)
        ]
        .sort_values("revenue_per_product", ascending=False)
        .head(12)
        .sort_values("revenue_per_product")
        .copy()
    )

    if eff_df.empty:
        st.info("Không đủ dữ liệu để vẽ biểu đồ hiệu suất seller.")
    else:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=eff_df["revenue_per_product"],
                y=eff_df["seller_label"],
                mode="markers",
                marker=dict(
                    size=14,
                    color=eff_df["review_rating"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Review<br>rating"),
                    line=dict(width=1, color="white"),
                ),
                customdata=np.stack(
                    [
                        eff_df["estimated_revenue"].map(money_short),
                        eff_df["product_count"],
                        eff_df["sold_quantity"],
                        eff_df["category_count"],
                        eff_df["review_rating"].round(2),
                    ],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Doanh thu/SP: %{x:,.0f} đ"
                    "<br>Tổng doanh thu: %{customdata[0]}"
                    "<br>Số sản phẩm: %{customdata[1]:,.0f}"
                    "<br>Lượt bán: %{customdata[2]:,.0f}"
                    "<br>Số ngành: %{customdata[3]:,.0f}"
                    "<br>Review rating: %{customdata[4]:.2f}/5"
                    "<extra></extra>"
                ),
            )
        )

        for _, row in eff_df.iterrows():
            fig.add_shape(
                type="line",
                x0=0,
                x1=row["revenue_per_product"],
                y0=row["seller_label"],
                y1=row["seller_label"],
                line=dict(
                    color="rgba(255,255,255,0.22)",
                    width=2,
                ),
            )

        fig.update_layout(
            title="Top seller theo doanh thu trung bình trên mỗi sản phẩm",
            showlegend=False,
        )

        fig.update_xaxes(title="Doanh thu ước tính / sản phẩm", tickformat="~s")
        fig.update_yaxes(title="Người bán")

        plot_chart(fig, height=540, hovermode="closest")

     

    # =============================
    # CHART 4: SELLER PORTFOLIO TREEMAP
    # =============================
    section(
        "4. Quy mô doanh thu và độ phủ danh mục của người bán",
        "Mục tiêu: xác định seller nào vừa tạo doanh thu lớn vừa kinh doanh trên nhiều ngành hàng.",
    )

    tree_df = (
        seller[seller["estimated_revenue"] > 0]
        .sort_values(["estimated_revenue", "category_count"], ascending=[False, False])
        .head(18)
        .copy()
    )

    if tree_df.empty:
        st.info("Không đủ dữ liệu để vẽ treemap seller.")
    else:
        tree_df["revenue_text"] = tree_df["estimated_revenue"].map(money_short)
        tree_df["review_rating_text"] = tree_df["review_rating"].apply(
            lambda x: f"{x:.2f}/5" if pd.notna(x) else "Chưa có review"
        )
        tree_df["bad_review_rate_text"] = tree_df["bad_review_rate"].apply(
            lambda x: pct(x * 100)
        )

        fig = go.Figure(
            go.Treemap(
                labels=tree_df["seller_label"],
                parents=[""] * len(tree_df),
                values=tree_df["estimated_revenue"],
                marker=dict(
                    colors=tree_df["category_count"],
                    colorscale="Blues",
                    colorbar=dict(title="Số<br>ngành"),
                    line=dict(width=1, color="rgba(255,255,255,0.25)"),
                ),
                customdata=np.stack(
                    [
                        tree_df["revenue_text"],
                        tree_df["sold_quantity"],
                        tree_df["product_count"],
                        tree_df["category_count"],
                        tree_df["review_rating_text"],
                        tree_df["bad_review_rate_text"],
                    ],
                    axis=-1,
                ),
                texttemplate="<b>%{label}</b><br>%{customdata[0]}",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Doanh thu: %{customdata[0]}"
                    "<br>Lượt bán: %{customdata[1]:,.0f}"
                    "<br>Sản phẩm: %{customdata[2]:,.0f}"
                    "<br>Số ngành: %{customdata[3]:,.0f}"
                    "<br>Review rating: %{customdata[4]}"
                    "<br>Bad review rate: %{customdata[5]}"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title="Treemap doanh thu seller, tô màu theo số ngành kinh doanh",
            margin=dict(l=20, r=20, t=70, b=20),
        )

        plot_chart(fig, height=560, hovermode="closest")

       
    # =============================
    # CHART 5: SELLER RISK HEATMAP
    # =============================
    section(
        "5. Ma trận rủi ro seller theo rating và bad review",
        "Mục tiêu: xem doanh thu đang tập trung ở nhóm seller chất lượng tốt hay nhóm có rủi ro review xấu.",
    )

    risk_df = seller[
        (seller["estimated_revenue"] > 0)
        & (seller["review_count"] > 0)
    ].copy()

    if risk_df.empty:
        st.info("Không đủ dữ liệu review để vẽ heatmap rủi ro seller.")
    else:
        risk_df["seller_rating_filled"] = risk_df["seller_rating"].fillna(0)

        rating_bins = [0, 3.5, 4.0, 4.5, 5.0]
        rating_labels = ["≤3.5", "3.5–4.0", "4.0–4.5", "4.5–5.0"]

        bad_bins = [0, 0.02, 0.05, 0.10, 1.0]
        bad_labels = ["≤2%", "2–5%", "5–10%", ">10%"]

        risk_df["seller_rating_group"] = pd.cut(
            risk_df["seller_rating_filled"],
            bins=rating_bins,
            labels=rating_labels,
            include_lowest=True,
        )

        risk_df["bad_review_group"] = pd.cut(
            risk_df["bad_review_rate"],
            bins=bad_bins,
            labels=bad_labels,
            include_lowest=True,
        )

        pivot_revenue = risk_df.pivot_table(
            index="bad_review_group",
            columns="seller_rating_group",
            values="estimated_revenue",
            aggfunc="sum",
            fill_value=0,
            observed=False,
        )

        pivot_count = risk_df.pivot_table(
            index="bad_review_group",
            columns="seller_rating_group",
            values="seller_name",
            aggfunc="nunique",
            fill_value=0,
            observed=False,
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_revenue.values,
                x=[str(x) for x in pivot_revenue.columns],
                y=[str(y) for y in pivot_revenue.index],
                colorscale="YlOrRd",
                text=np.vectorize(money_short)(pivot_revenue.values),
                texttemplate="%{text}",
                customdata=pivot_count.values,
                hovertemplate=(
                    "Seller rating: %{x}<br>"
                    "Bad review rate: %{y}<br>"
                    "Doanh thu: %{z:,.0f} đ"
                    "<br>Số seller: %{customdata:,.0f}"
                    "<extra></extra>"
                ),
                colorbar=dict(title="Doanh<br>thu"),
            )
        )

        fig.update_layout(
            title="Doanh thu theo nhóm Seller rating và tỷ lệ bad review",
            showlegend=False,
        )

        fig.update_xaxes(title="Nhóm Seller rating")
        fig.update_yaxes(title="Nhóm bad review rate")

        plot_chart(fig, height=480, hovermode="closest")

    

    # =============================
    # TABLE
    # =============================
    section(
        "Bảng chi tiết người bán",
        "Dùng bảng này để kiểm chứng số liệu biểu đồ và lấy số đưa vào báo cáo.",
    )

    table = seller.sort_values("estimated_revenue", ascending=False).copy()

    table["Doanh thu"] = table["estimated_revenue"].apply(money_short)
    table["Lượt bán"] = table["sold_quantity"].apply(fmt_int)
    table["Số sản phẩm"] = table["product_count"].apply(fmt_int)
    table["Số ngành"] = table["category_count"].apply(fmt_int)
    table["Coupon rate"] = table["coupon_rate"].apply(lambda x: pct(x * 100))
    table["Discount TB"] = table["avg_discount"].map(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    table["Bad review rate"] = table["bad_review_rate"].apply(lambda x: pct(x * 100))
    table["Product rating"] = table["product_rating"].round(2)
    table["Review rating"] = table["review_rating"].round(2)
    table["Seller rating"] = table["seller_rating"].round(2)

    st.dataframe(
        table[
            [
                "seller_name",
                "Số sản phẩm",
                "Số ngành",
                "Lượt bán",
                "Doanh thu",
                "Coupon rate",
                "Discount TB",
                "Bad review rate",
                "Product rating",
                "Review rating",
                "Seller rating",
            ]
        ].rename(columns={"seller_name": "Người bán"}),
        use_container_width=True,
        hide_index=True,
    )