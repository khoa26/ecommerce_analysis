import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from config import COLOR_PRIMARY

def render_price_discount_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Giá & ưu đãi")

    cols = [
        "product_id", "category_name", "seller_name",
        "current_price", "original_price", "discount_percent",
        "coupon_discount_amount", "has_coupon"
    ]

    df = mart_filtered[cols].copy()

    # clean
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["current_price"])

    st.markdown("#### 📊 Phân tích cơ bản")

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.histogram(
            df,
            x="current_price",
            nbins=80,
            title="Phân bố giá hiện tại",
            color_discrete_sequence=[COLOR_PRIMARY],
        )
        fig1.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig1, width="stretch")

    with c2:
        fig2 = px.histogram(
            df.dropna(subset=["discount_percent"]),
            x="discount_percent",
            nbins=50,
            title="Phân bố mức giảm giá",
            color_discrete_sequence=["#FFB020"],
        )
        fig2.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2, width="stretch")

    # Scatter giá vs giảm giá
    df_scatter = df.dropna(subset=["current_price", "discount_percent"])

    if not df_scatter.empty:
        fig3 = px.scatter(
            df_scatter,
            x="discount_percent",
            y="current_price",
            trendline="ols",
            opacity=0.3,
            title="Quan hệ giá và mức giảm (OLS)",
            color_discrete_sequence=["#22C55E"],
        )
        fig3.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig3, width="stretch")

    st.markdown("#### 🏷️ Phân tích theo ngành hàng & người bán")

    df_p2 = df.dropna(subset=["category_name"])

    cat_summary = (
        df_p2.groupby("category_name")
        .agg(
            avg_price=("current_price", "mean"),
            avg_discount=("discount_percent", "mean"),
            product_count=("product_id", "count"),
        )
        .reset_index()
    )

    # cat_summary = cat_summary[cat_summary["product_count"] >= 50]

    c1, c2 = st.columns(2)

    with c1:
        fig4 = px.bar(
            cat_summary.sort_values("avg_price", ascending=False).head(15),
            x="avg_price",
            y="category_name",
            orientation="h",
            title="Top ngành hàng giá cao",
            color="avg_price",
            color_continuous_scale="Blues",
        )
        fig4.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig4, width="stretch")

    with c2:
        fig5 = px.bar(
            cat_summary.sort_values("avg_discount", ascending=False).head(15),
            x="avg_discount",
            y="category_name",
            orientation="h",
            title="Top ngành hàng giảm giá mạnh",
            color="avg_discount",
            color_continuous_scale="Reds",
        )
        fig5.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig5, width="stretch")

    seller_summary = (
        df.groupby("seller_name")
        .agg(avg_price=("current_price", "mean"), product_count=("product_id", "count"))
        .reset_index()
    )

    # seller_summary = seller_summary[seller_summary["product_count"] >= 20]

    fig6 = px.bar(
        seller_summary.sort_values("avg_price", ascending=False).head(15),
        x="avg_price",
        y="seller_name",
        orientation="h",
        title="Top seller theo giá trung bình",
        color="avg_price",
        color_continuous_scale="Teal",
    )
    fig6.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig6, width="stretch")


    st.markdown("#### 🎟️ Phân tích Coupon & giảm giá thực")

    df_coupon = df.copy()

    df_coupon["coupon_discount_amount"] = df_coupon["coupon_discount_amount"].fillna(0)
    df_coupon["has_coupon"] = df_coupon["coupon_discount_amount"] > 0

    # final price
    df_coupon["final_price"] = df_coupon["current_price"] - df_coupon["coupon_discount_amount"]
    df_coupon["final_price"] = df_coupon["final_price"].clip(lower=0)

    # real discount
    df_coupon["real_discount_percent"] = (
        (df_coupon["original_price"] - df_coupon["final_price"])
        / df_coupon["original_price"]
        * 100
    )
    df_coupon["real_discount_percent"] = df_coupon["real_discount_percent"].replace([np.inf, -np.inf], 0).fillna(0)

    c1, c2 = st.columns(2)

    with c1:
        fig7 = px.box(
            df_coupon,
            x="has_coupon",
            y="current_price",
            title="Giá: Có vs Không có coupon",
            color="has_coupon",
        )
        fig7.update_yaxes(type="log")
        fig7.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig7, width="stretch")

    with c2:
        df_scatter2 = df_coupon[df_coupon["has_coupon"] == True]

        if not df_scatter2.empty:
            fig8 = px.scatter(
                df_scatter2,
                x="discount_percent",
                y="real_discount_percent",
                opacity=0.4,
                title="Giảm giá hiển thị vs thực tế",
            )
            fig8.add_shape(
                type="line",
                x0=0,
                y0=0,
                x1=100,
                y1=100,
                line=dict(color="red", dash="dash"),
            )
            fig8.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig8, width="stretch")

    cat_coupon = (
        df_coupon[df_coupon["has_coupon"] == True]
        .groupby("category_name")["coupon_discount_amount"]
        .mean()
        .reset_index()
        .sort_values("coupon_discount_amount", ascending=False)
        .head(10)
    )

    fig9 = px.bar(
        cat_coupon,
        x="coupon_discount_amount",
        y="category_name",
        orientation="h",
        title="Top ngành hàng coupon cao",
        color="coupon_discount_amount",
    )
    fig9.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig9, width="stretch")

    seller_discount = (
        df_coupon.groupby("seller_name")
        .agg(
            avg_discount=("real_discount_percent", "mean"),
            product_count=("product_id", "count"),
        )
        .reset_index()
    )

    seller_discount = seller_discount[seller_discount["product_count"] >= 20]

    fig10 = px.bar(
        seller_discount.sort_values("avg_discount", ascending=False).head(15),
        x="avg_discount",
        y="seller_name",
        orientation="h",
        title="Top seller giảm giá mạnh nhất",
        color="avg_discount",
        color_continuous_scale="Inferno",
    )
    fig10.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig10, width="stretch")