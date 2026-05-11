import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from config import COLOR_PRIMARY
from data_engine import load_tables, get_processed_signature
import plotly.graph_objects as go


def render_price_discount_tab(mart_filtered: pd.DataFrame, price_offer: pd.DataFrame):

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

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["current_price"])

    num_cols = ["current_price", "original_price", "discount_percent", "coupon_discount_amount"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["coupon_discount_amount"] = df.get("coupon_discount_amount", 0).fillna(0)

    df["final_price"] = df["current_price"] - df["coupon_discount_amount"]
    df["final_price"] = df["final_price"].clip(lower=0)

    df["real_discount_percent"] = (
        (df["original_price"] - df["final_price"]) / df["original_price"] * 100
    )
    df["real_discount_percent"] = df["real_discount_percent"].replace([np.inf, -np.inf], 0).fillna(0)

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

    df_scatter = df.dropna(subset=["current_price", "discount_percent"])

    if not df_scatter.empty:
        fig3 = px.scatter(
            df_scatter,
            x="discount_percent",
            y="current_price",
            trendline="lowess",
            opacity=0.3,
            title="Quan hệ giữa giá và giảm giá",
            labels={
                "discount_percent": "Giảm giá (%)",
                "current_price": "Giá (VND)"
            },
        )
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

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

    st.divider()
    st.markdown("#### ⏱️ Xu hướng Giá & Ưu đãi theo thời gian")

    with st.spinner("Đang tải dữ liệu lịch sử giá..."):
        try:
            # Lọc sản phẩm thuộc top bán chạy (Lấy từ bảng mart_filtered đang có sẵn trên Dashboard)
            top_products_df = df.copy()
            if "level" in top_products_df.columns:
                top_products_df = top_products_df[top_products_df['level'] == 1]
                
            if "sold_quantity" in top_products_df.columns:
                top_product_ids = top_products_df.nlargest(500, 'sold_quantity')['product_id'].unique()
            else:
                top_product_ids = top_products_df['product_id'].unique()[:500]
                
            # Tạo bảng mapping để lấy coupon từ mart_filtered áp dụng cho lịch sử giá
            coupon_map = df[['product_id', 'coupon_discount_amount']].drop_duplicates('product_id')

            # Tối ưu: Chỉ lọc lịch sử giá của top sản phẩm
            df_trend = price_offer[price_offer['product_id'].astype(str).isin(top_product_ids.astype(str))].copy()
            
            if df_trend.empty:
                st.info("Không có lịch sử giá cho các sản phẩm Top bán chạy này.")
                return

            # Xử lý thời gian và kiểu dữ liệu
            df_trend['crawl_time'] = pd.to_datetime(df_trend['crawl_time'], errors='coerce')
            df_trend = df_trend.dropna(subset=['crawl_time'])
            df_trend['date'] = df_trend['crawl_time'].dt.date
            
            df_trend['current_price'] = pd.to_numeric(df_trend['current_price'], errors='coerce')
            df_trend['discount_percent'] = pd.to_numeric(df_trend['discount_percent'], errors='coerce')
            
            # --- ĐOẠN CODE CẦN SỬA ---
            # Đồng bộ kiểu dữ liệu (ép về string) trước khi merge để tránh lỗi int64 vs str
            df_trend['product_id'] = df_trend['product_id'].astype(str)
            coupon_map['product_id'] = coupon_map['product_id'].astype(str)

            # Join với coupon_map để tính final_price trong quá khứ
            df_trend = df_trend.merge(coupon_map, on='product_id', how='left')
            
            df_trend['coupon_discount_amount'] = df_trend['coupon_discount_amount'].fillna(0)
            df_trend['final_price'] = (df_trend['current_price'] - df_trend['coupon_discount_amount']).clip(lower=0)
            # --------------------------

            # Time Aggregation
            daily_agg = df_trend.groupby('date').agg(
                median_current_price=('current_price', 'mean'),
                median_final_price=('final_price', 'mean'),
                median_discount=('discount_percent', 'mean')
            ).reset_index().sort_values('date')

            if len(daily_agg) < 2:
                st.info("Dữ liệu cần tối thiểu 2 ngày lấy mẫu để vẽ xu hướng.")
                return

            # Smoothing
            daily_agg['smooth_current_price'] = daily_agg['median_current_price'].rolling(window=3, min_periods=1).mean()
            daily_agg['smooth_final_price'] = daily_agg['median_final_price'].rolling(window=3, min_periods=1).mean()
            daily_agg['smooth_discount'] = daily_agg['median_discount'].rolling(window=3, min_periods=1).mean()

            # Tính Metrics Insights
            start_price = daily_agg['smooth_final_price'].iloc[0]
            end_price = daily_agg['smooth_final_price'].iloc[-1]
            pct_change = ((end_price - start_price) / start_price * 100) if start_price > 0 else 0

            max_idx = daily_agg['smooth_final_price'].idxmax()
            min_idx = daily_agg['smooth_final_price'].idxmin()

            max_price = daily_agg.loc[max_idx, 'smooth_final_price']
            max_date = daily_agg.loc[max_idx, 'date'].strftime('%d/%m/%Y')
            min_price = daily_agg.loc[min_idx, 'smooth_final_price']
            min_date = daily_agg.loc[min_idx, 'date'].strftime('%d/%m/%Y')

            if pct_change > 1:
                trend_label, trend_color = "📈 Tăng giá", "normal"
            elif pct_change < -1:
                trend_label, trend_color = "📉 Giảm giá", "inverse"
            else:
                trend_label, trend_color = "➡️ Ổn định", "off"

            # Render Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Biến động (Đầu -> Cuối)", trend_label, f"{pct_change:+.1f}%", delta_color=trend_color)
            c2.metric("Giá trung vị hiện tại", f"{end_price:,.0f} ₫")
            c3.metric(f"Đỉnh giá ({max_date})", f"{max_price:,.0f} ₫")
            c4.metric(f"Đáy giá ({min_date})", f"{min_price:,.0f} ₫")

            st.markdown("<br>", unsafe_allow_html=True)

            # Dual-Axis Line Chart
            fig9 = go.Figure()

            # Trace 1: Giá cuối
            fig9.add_trace(go.Scatter(
                x=daily_agg['date'], y=daily_agg['smooth_final_price'],
                mode='lines', name='Giá cuối (Sau Coupon)',
                line=dict(color='#1f77b4', width=3),
                hovertemplate='Giá cuối: <b>%{y:,.0f} ₫</b><extra></extra>'
            ))

            # Trace 2: Giá niêm yết
            fig9.add_trace(go.Scatter(
                x=daily_agg['date'], y=daily_agg['smooth_current_price'],
                mode='lines', name='Giá niêm yết',
                line=dict(color='#aec7e8', width=2, dash='dash'),
                hovertemplate='Giá niêm yết: %{y:,.0f} ₫<extra></extra>'
            ))

            # Trace 3: % Giảm giá
            fig9.add_trace(go.Scatter(
                x=daily_agg['date'], y=daily_agg['smooth_discount'],
                mode='lines', name='Giảm giá (%)',
                yaxis='y2',
                line=dict(color='#ff7f0e', width=2),
                hovertemplate='Giảm giá: <b>%{y:.1f}%</b><extra></extra>'
            ))

            fig9.update_layout(
                title="Biến động Giá (VND) và Mức giảm giá (%) theo thời gian",
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(title='Ngày lấy dữ liệu', showgrid=True, gridcolor='#f0f0f0', tickformat='%d/%m/%Y'),
                yaxis=dict(title='Mức giá (VND)', tickformat=',.0f', side='left', showgrid=True, gridcolor='#f0f0f0'),
                yaxis2=dict(title='Mức giảm giá (%)', overlaying='y', side='right', tickformat='.1f', showgrid=False),
                margin=dict(l=0, r=0, t=60, b=0),
                height=450
            )

            st.plotly_chart(fig9, use_container_width=True)
            
        except Exception as e:
            st.error(f"Đã xảy ra lỗi khi tính toán xu hướng giá: {str(e)}")