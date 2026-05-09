import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from config import COLOR_PRIMARY


def render_price_discount_tab(mart_filtered: pd.DataFrame):
    st.markdown("### 💰 Giá & ưu đãi")

    # =============================
    # SAFE COLUMN SELECTION
    # =============================
    required_cols = [
        "product_id", "category_name", "seller_name",
        "current_price", "original_price", "discount_percent",
        "coupon_discount_amount", "has_coupon"
    ]

    available_cols = [c for c in required_cols if c in mart_filtered.columns]
    df = mart_filtered[available_cols].copy()

    if df.empty:
        st.info("Không có dữ liệu giá.")
        return

    # =============================
    # CLEAN DATA
    # =============================
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["current_price"])

    # Fix numeric
    num_cols = ["current_price", "original_price", "discount_percent", "coupon_discount_amount"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =============================
    # FEATURE ENGINEERING 🔥
    # =============================
    df["coupon_discount_amount"] = df.get("coupon_discount_amount", 0).fillna(0)

    df["final_price"] = df["current_price"] - df["coupon_discount_amount"]
    df["final_price"] = df["final_price"].clip(lower=0)

    df["real_discount_percent"] = (
        (df["original_price"] - df["final_price"]) / df["original_price"] * 100
    )
    df["real_discount_percent"] = df["real_discount_percent"].replace([np.inf, -np.inf], 0).fillna(0)

    # =============================
    # BASIC ANALYSIS
    # =============================
    st.markdown("#### 📊 Phân tích cơ bản")

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.histogram(
            df,
            x="current_price",
            nbins=80,
            title="Phân bố giá bán hiện tại",
            labels={"current_price": "Giá hiện tại (VND)"},
            color_discrete_sequence=[COLOR_PRIMARY],
        )
        fig1.update_yaxes(title="Số lượng sản phẩm")
        fig1.update_layout(height=350)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.histogram(
            df.dropna(subset=["discount_percent"]),
            x="discount_percent",
            nbins=50,
            title="Phân bố mức giảm giá (%)",
            labels={"discount_percent": "Phần trăm giảm giá (%)"},
            color_discrete_sequence=["#FFB020"],
        )
        fig2.update_yaxes(title="Số lượng sản phẩm")
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    # =============================
    # RELATIONSHIP
    # =============================
    df_scatter = df.dropna(subset=["current_price", "discount_percent"])

    if not df_scatter.empty:
        fig3 = px.scatter(
            df_scatter,
            x="discount_percent",
            y="current_price",
            trendline="ols",
            opacity=0.3,
            title="Quan hệ giữa giá và giảm giá",
            labels={
                "discount_percent": "Giảm giá (%)",
                "current_price": "Giá (VND)"
            },
        )
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

    # =============================
    # CATEGORY & SELLER
    # =============================
    st.markdown("#### 🏷️ Phân tích theo ngành hàng & nhà bán")

    df_cat = df.dropna(subset=["category_name"])

    cat_summary = (
        df_cat.groupby("category_name")
        .agg(
            avg_price=("current_price", "mean"),
            avg_discount=("discount_percent", "mean"),
            avg_real_discount=("real_discount_percent", "mean"),
            product_count=("product_id", "count"),
        )
        .reset_index()
    )

    c1, c2 = st.columns(2)

    with c1:
        fig4 = px.bar(
            cat_summary.sort_values("avg_price", ascending=False).head(15),
            x="avg_price",
            y="category_name",
            orientation="h",
            title="Top ngành hàng giá cao",
            labels={"avg_price": "Giá trung bình", "category_name": "Ngành hàng"},
            color="avg_price",
        )
        st.plotly_chart(fig4, use_container_width=True)

    with c2:
        fig5 = px.bar(
            cat_summary.sort_values("avg_real_discount", ascending=False).head(15),
            x="avg_real_discount",
            y="category_name",
            orientation="h",
            title="Top ngành hàng giảm giá THỰC mạnh",
            labels={"avg_real_discount": "% giảm thật", "category_name": "Ngành hàng"},
            color="avg_real_discount",
        )
        st.plotly_chart(fig5, use_container_width=True)

    # =============================
    # SELLER ANALYSIS
    # =============================
    seller_summary = (
        df.groupby("seller_name")
        .agg(
            avg_price=("current_price", "mean"),
            avg_real_discount=("real_discount_percent", "mean"),
            product_count=("product_id", "count"),
        )
        .reset_index()
    )

    seller_summary = seller_summary[seller_summary["product_count"] >= 20]

    fig6 = px.bar(
        seller_summary.sort_values("avg_real_discount", ascending=False).head(15),
        x="avg_real_discount",
        y="seller_name",
        orientation="h",
        title="Top nhà bán giảm giá mạnh nhất (THỰC)",
        labels={"avg_real_discount": "% giảm thật", "seller_name": "Nhà bán"},
        color="avg_real_discount",
    )
    st.plotly_chart(fig6, use_container_width=True)

    # =============================
    # COUPON INSIGHT 🔥
    # =============================
    st.markdown("#### 🎟️ Coupon & giảm giá thực")

    c1, c2 = st.columns(2)

    with c1:
        fig7 = px.box(
            df,
            x="has_coupon",
            y="final_price",
            title="Giá sau coupon",
            labels={
                "has_coupon": "Có coupon",
                "final_price": "Giá cuối"
            },
            color="has_coupon",
        )
        fig7.update_yaxes(type="log")
        st.plotly_chart(fig7, use_container_width=True)

    with c2:
        df_coupon = df[df["has_coupon"] == True]

        if not df_coupon.empty:
            fig8 = px.scatter(
                df_coupon,
                x="discount_percent",
                y="real_discount_percent",
                opacity=0.4,
                title="Giảm giá hiển thị vs thực tế",
                labels={
                    "discount_percent": "Giảm hiển thị (%)",
                    "real_discount_percent": "Giảm thực (%)"
                },
            )

            fig8.add_shape(
                type="line",
                x0=0, y0=0, x1=100, y1=100,
                line=dict(color="red", dash="dash"),
            )

            st.plotly_chart(fig8, use_container_width=True)