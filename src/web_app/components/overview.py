import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np

from config import COLOR_PRIMARY, vnd, fmt_int, pct


def render_overview_tab(mart_filtered: pd.DataFrame):
    st.markdown("### Tổng quan hệ thống thương mại điện tử")

    st.markdown(
        """
        Trang này cung cấp cái nhìn nhanh về toàn bộ hệ thống: quy mô sản phẩm,
        ngành hàng, người bán, sức bán, giá bán, ưu đãi và mức độ phản hồi từ khách hàng.
        """
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

    df["sold_quantity"] = df["sold_quantity"].fillna(0)
    df["review_count"] = df["review_count"].fillna(0)
    df["coupon_discount_amount"] = df["coupon_discount_amount"].fillna(0)
    df["has_coupon"] = df["coupon_discount_amount"] > 0

    df["estimated_revenue"] = (
        df["current_price"].fillna(0) * df["sold_quantity"].fillna(0)
    )

    # =========================
    # KPI TỔNG QUAN
    st.markdown("#### Chỉ số tổng quan")

    total_products = df["product_id"].nunique() if "product_id" in df.columns else len(df)
    total_categories = df["category_name"].nunique() if "category_name" in df.columns else 0
    total_sellers = df["seller_name"].nunique() if "seller_name" in df.columns else 0

    total_sold = df["sold_quantity"].sum()
    total_reviews = df["review_count"].sum()
    avg_price = df["current_price"].dropna().mean()
    avg_discount = df["discount_percent"].dropna().mean()
    coupon_rate = df["has_coupon"].mean() * 100
    avg_rating = df["review_score"].dropna().mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric(
            "Sản phẩm",
            fmt_int(total_products),
            f"{fmt_int(total_categories)} ngành hàng",
        )

    with k2:
        st.metric(
            "Người bán",
            fmt_int(total_sellers),
            f"{fmt_int(total_sold)} lượt bán",
        )

    with k3:
        st.metric(
            "Giá trung bình",
            vnd(avg_price),
            f"Giảm TB: {pct(avg_discount)}",
        )

    with k4:
        rating_text = f"{avg_rating:.2f}/5" if not np.isnan(avg_rating) else "—"
        st.metric(
            "Đánh giá TB",
            rating_text,
            f"{fmt_int(total_reviews)} lượt review",
        )

    st.markdown("---")

    # =========================
    # MỤC TIÊU TỔNG QUAN
    st.markdown("#### Mục tiêu tổng quan")

    c_goal1, c_goal2, c_goal3, c_goal4 = st.columns(4)

    with c_goal1:
        st.info("**MT1:** Đánh giá quy mô hệ thống qua sản phẩm, ngành hàng và người bán.")

    with c_goal2:
        st.info("**MT2:** Nhận diện nhóm ngành hàng đóng góp lớn về lượt bán.")

    with c_goal3:
        st.info("**MT3:** Nắm nhanh mặt bằng giá và mức độ sử dụng ưu đãi.")

    with c_goal4:
        st.info("**MT4:** Quan sát tín hiệu chất lượng qua rating và review.")

    st.markdown("---")

    # =========================
    # BIỂU ĐỒ 1 + 2:
    # CƠ CẤU NGÀNH HÀNG & SỨC BÁN

    st.markdown("#### Bức tranh chung theo ngành hàng")

    category_summary = (
        df.groupby("category_name", dropna=False)
        .agg(
            product_count=("product_id", "count"),
            sold_quantity=("sold_quantity", "sum"),
            review_count=("review_count", "sum"),
            avg_price=("current_price", "mean"),
            avg_rating=("review_score", "mean"),
            estimated_revenue=("estimated_revenue", "sum"),
        )
        .reset_index()
    )

    category_summary["category_name"] = category_summary["category_name"].fillna(
        "Không xác định"
    )

    c1, c2 = st.columns(2)

    with c1:
        top_category_product = (
            category_summary
            .sort_values("product_count", ascending=False)
            .head(10)
        )

        fig1 = px.treemap(
            top_category_product,
            path=["category_name"],
            values="product_count",
            color="product_count",
            color_continuous_scale="Blues",
            title="Cơ cấu sản phẩm theo ngành hàng",
        )
        fig1.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig1, width="stretch")

    with c2:
        top_category_sold = (
            category_summary
            .sort_values("sold_quantity", ascending=False)
            .head(10)
        )

        fig2 = px.bar(
            top_category_sold.sort_values("sold_quantity"),
            x="sold_quantity",
            y="category_name",
            orientation="h",
            color="sold_quantity",
            color_continuous_scale="Teal",
            title="Top ngành hàng theo lượt bán",
            labels={
                "sold_quantity": "Lượt bán",
                "category_name": "Ngành hàng",
            },
        )
        fig2.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2, width="stretch")

    # =========================
    # BIỂU ĐỒ 3 + 4:
    # GIÁ & ƯU ĐÃI Ở MỨC TỔNG QUAN
    st.markdown("#### Bức tranh chung về giá và ưu đãi")

    c3, c4 = st.columns(2)

    with c3:
        price_df = df.dropna(subset=["current_price"]).copy()

        if not price_df.empty:
            # Cắt bớt outlier để biểu đồ tổng quan dễ nhìn hơn
            upper_price = price_df["current_price"].quantile(0.98)
            price_df = price_df[price_df["current_price"] <= upper_price]

            fig3 = px.histogram(
                price_df,
                x="current_price",
                nbins=50,
                title="Phân bố giá sản phẩm",
                color_discrete_sequence=[COLOR_PRIMARY],
                labels={"current_price": "Giá hiện tại"},
            )
            fig3.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig3, width="stretch")
        else:
            st.info("Không đủ dữ liệu giá để hiển thị.")

    with c4:
        coupon_summary = (
            df.groupby("has_coupon")
            .agg(product_count=("product_id", "count"))
            .reset_index()
        )

        coupon_summary["Trạng thái coupon"] = coupon_summary["has_coupon"].map(
            {
                True: "Có coupon",
                False: "Không có coupon",
            }
        )

        fig4 = px.pie(
            coupon_summary,
            names="Trạng thái coupon",
            values="product_count",
            hole=0.45,
            title="Tỷ lệ sản phẩm có coupon",
        )
        fig4.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig4, width="stretch")

    # =========================
    # BIỂU ĐỒ 5:
    # TƯƠNG QUAN TỔNG QUAN GIỮA BÁN HÀNG VÀ ĐÁNH GIÁ

    st.markdown("#### Cơ cấu sản phẩm theo mức rating")

    rating_df = df.dropna(subset=["review_score"]).copy()

    rating_df["rating_group"] = pd.cut(
        rating_df["review_score"],
        bins=[0, 3, 4, 4.5, 5],
        labels=["Dưới 3", "3 - 4", "4 - 4.5", "4.5 - 5"],
        include_lowest=True
    )

    rating_summary = (
        rating_df.groupby("rating_group")
        .agg(product_count=("product_id", "count"))
        .reset_index()
    )

    fig5 = px.bar(
        rating_summary,
        x="rating_group",
        y="product_count",
        title="Cơ cấu sản phẩm theo nhóm điểm đánh giá",
        labels={
            "rating_group": "Nhóm rating",
            "product_count": "Số sản phẩm",
        },
        color="product_count",
        color_continuous_scale="Viridis",
    )

    fig5.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig5, use_container_width=True)

    # =========================
    # BẢNG TÓM TẮT 
   
    st.markdown("#### Tóm tắt nhanh theo ngành hàng")

    overview_table = (
        category_summary
        .sort_values("sold_quantity", ascending=False)
        .head(10)
        .copy()
    )

    overview_table["avg_price"] = overview_table["avg_price"].round(0)
    overview_table["avg_rating"] = overview_table["avg_rating"].round(2)
    overview_table["estimated_revenue"] = overview_table["estimated_revenue"].round(0)

    overview_table = overview_table.rename(
        columns={
            "category_name": "Ngành hàng",
            "product_count": "Số sản phẩm",
            "sold_quantity": "Lượt bán",
            "review_count": "Số review",
            "avg_price": "Giá TB",
            "avg_rating": "Rating TB",
            "estimated_revenue": "Doanh thu ước tính",
        }
    )

    st.dataframe(
    overview_table[
        [
            "Ngành hàng",
            "Số sản phẩm",
            "Lượt bán",
            "Số review",
            "Giá TB",
            "Rating TB",
            "Doanh thu ước tính",
        ]
    ],
    use_container_width=True,
    height=360,
)