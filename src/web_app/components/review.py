import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from pathlib import Path
from config import *

@st.cache_data(show_spinner=False)
def load_nlp_bad_reviews(path_str: str, mtime_ns: int | None, size: int | None) -> pd.DataFrame:
    try:
        return pd.read_parquet(path_str)
    except Exception:
        pass
    return pd.DataFrame()

def render_review_tab(mart_filtered: pd.DataFrame) -> None:

    if mart_filtered is None or mart_filtered.empty:
        st.info("Không có dữ liệu để hiển thị.")
        return

    df = mart_filtered.copy()
    
    # Remove inf and handle NA
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_valid = df.dropna(subset=['review_score', 'review_count'])
    
    if df_valid.empty:
        st.info("Không có dữ liệu đánh giá hợp lệ.")
        return

    # Common layout params
    chart_layout = dict(height=400, margin=dict(l=20, r=20, t=40, b=20))

    # =====================================================
    # SECTION 1: OVERVIEW KPIs
    # =====================================================
    st.markdown("### 1. Tổng quan chất lượng đánh giá")
    
    avg_score = df_valid['review_score'].mean()
    total_reviews = df_valid['review_count'].sum()
    
    # Calculate % based on products
    bad_pct = (df_valid['review_score'] <= 2).mean() * 100
    high_pct = (df_valid['review_score'] >= 4).mean() * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi("Điểm đánh giá TB", f"{avg_score:.2f}/5")
    with col2:
        render_kpi("Tổng lượt đánh giá", f"{total_reviews:,.0f}")
    with col3:
        render_kpi("Tỷ lệ SP điểm thấp (≤ 2)", f"{bad_pct:.1f}%")
    with col4:
        render_kpi("Tỷ lệ SP điểm cao (≥ 4)", f"{high_pct:.1f}%")

    st.divider()

    # =====================================================
    # SECTION 2: DISTRIBUTION
    # =====================================================
    st.markdown("### 2. Phân bố đánh giá")
    d_col1, d_col2 = st.columns(2)

    with d_col1:
        fig_dist1 = px.histogram(
            df_valid, 
            x='review_score', 
            nbins=20,
            title="Phân bố điểm đánh giá",
            labels={
                "review_score": "Điểm đánh giá",
                "count": "Số lượng sản phẩm"
            },
            color_discrete_sequence=['#3b82f6']
        )
        fig_dist1.update_layout(**chart_layout)
        fig_dist1.update_yaxes(title="Số lượng sản phẩm")
        st.plotly_chart(fig_dist1, use_container_width=True)

    with d_col2:
        # Use log_y to handle right-skewed count distributions safely
        fig_dist2 = px.histogram(
            df_valid, 
            x='review_count', 
            nbins=50,
            log_y=True,
            title="Phân bố số lượng đánh giá (thang log)",
            labels={
                "review_count": "Số lượt đánh giá",
                "count": "Số lượng sản phẩm"
            },
            color_discrete_sequence=['#8b5cf6']
        )
        fig_dist2.update_layout(**chart_layout)
        fig_dist2.update_yaxes(title="Số lượng sản phẩm")
        st.plotly_chart(fig_dist2, use_container_width=True)

    st.divider()

    # =====================================================
    # SECTION 3: RELATIONSHIPS
    # =====================================================
    st.markdown("### 3. Mối quan hệ giữa các chỉ số")
    r_col1, r_col2 = st.columns(2)

    with r_col1:
        fig_rel1 = px.scatter(
            df_valid, 
            x='review_count', 
            y='review_score',
            opacity=0.4,
            # trendline="lowess",
            title="Mối quan hệ: Điểm đánh giá và số lượt đánh giá",
            labels={
                "review_count": "Số lượt đánh giá",
                "review_score": "Điểm đánh giá"
            },
            color_discrete_sequence=['#ef4444']
        )
        fig_rel1.update_layout(**chart_layout)
        st.plotly_chart(fig_rel1, use_container_width=True)

    with r_col2:
        df_sold = df_valid.dropna(subset=['sold_quantity'])
        if not df_sold.empty:
            fig_rel2 = px.scatter(
                df_sold, 
                x='sold_quantity', 
                y='review_score',
                opacity=0.4,
                # trendline="lowess",
                title="Mối quan hệ: Điểm đánh giá và số lượng bán",
                labels={
                    "sold_quantity": "Số lượng bán",
                    "review_score": "Điểm đánh giá"
                },
                color_discrete_sequence=['#10b981']
            )
            fig_rel2.update_xaxes(type='log') # sold_quantity often skewed
            fig_rel2.update_layout(**chart_layout)
            st.plotly_chart(fig_rel2, use_container_width=True)
        else:
            st.info("Không có dữ liệu Số lượng bán (sold_quantity)")

    st.divider()

    # =====================================================
    # SECTION 4 & 7: TOP WORST PRODUCTS & ADVANCED INSIGHT
    # =====================================================
    st.markdown("### 4. Cảnh báo Sản phẩm (Nguy hiểm & Bất mãn)")
    df_valid = df_valid.copy()
    # Calculate dissatisfaction score
    df_valid['dissatisfaction_score'] = df_valid['review_count'] * (5 - df_valid['review_score'])
    
    w_col1, w_col2 = st.columns(2)

    with w_col1:
        st.markdown("**Top Sản phẩm Điểm thấp nhất (Review Count > 10)**")
        worst_products = df_valid[df_valid['review_count'] > 10].sort_values('review_score', ascending=True)
        if not worst_products.empty:
            st.dataframe(
                worst_products[['product_name', 'review_score', 'review_count']].head(10),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Không có sản phẩm nào điểm thấp với lượt review > 10.")

    with w_col2:
        st.markdown("**Top 15 Sản phẩm có Chỉ số Bất mãn (Dissatisfaction) cao nhất**")
        top_dissatisfied = df_valid.nlargest(15, 'dissatisfaction_score').sort_values('dissatisfaction_score', ascending=True)
        
        def truncate_text(text, max_len=30):
            return text if len(text) <= max_len else text[:max_len] + "..."

        top_dissatisfied["product_name_short"] = top_dissatisfied["product_name"].apply(truncate_text)

        if not top_dissatisfied.empty:
            fig_dis = px.bar(
                top_dissatisfied, 
                x='dissatisfaction_score', 
                y='product_name_short',
                orientation='h',
                title="Top sản phẩm có chỉ số bất mãn cao nhất",
                labels={
                    "dissatisfaction_score": "Chỉ số bất mãn",
                    "product_name_short": "Tên sản phẩm"
                },
                color='dissatisfaction_score',
                color_continuous_scale='Reds'
            )
            fig_dis.update_layout(**chart_layout)
            st.plotly_chart(fig_dis, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu.")

    st.divider()

    # =====================================================
    # SECTION 5: CATEGORY INSIGHT
    # =====================================================
    st.markdown("### 5. Điểm đánh giá theo Ngành hàng")
    if 'category_name' in df_valid.columns:
        cat_stats = df_valid.groupby('category_name').agg(
            avg_review_score=('review_score', 'mean'),
            product_count=('review_score', 'count')
        ).reset_index()
        
        cat_stats = cat_stats[cat_stats['product_count'] > 20].sort_values('avg_review_score', ascending=False)
        
        if not cat_stats.empty:
            fig_cat = px.bar(
                cat_stats, 
                x='category_name', 
                y='avg_review_score',
                color='avg_review_score',
                title="Điểm đánh giá trung bình theo ngành hàng",
                labels={
                    "category_name": "Ngành hàng",
                    "avg_review_score": "Điểm đánh giá trung bình"
                },
                color_continuous_scale='Viridis'
            )
            # Limit y-axis to better show differences (usually between 3.0 and 5.0)
            min_y = max(0, cat_stats['avg_review_score'].min() - 0.2)
            fig_cat.update_yaxes(range=[min_y, 5.0])
            fig_cat.update_layout(height=450, margin=dict(l=20, r=20, t=40, b=100))
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Không có ngành hàng nào đủ số lượng sản phẩm để so sánh.")
    else:
        st.warning("Thiếu cột category_name")

    st.divider()

    st.markdown("### 6. Phân tích Nguyên nhân Đánh giá Xấu (LDA NLP)")
    path = PROCESSED_POWERBI_DIR / "lda_bad_reviews_topics.parquet"
    if not path.exists():
        st.info("Không tìm thấy dữ liệu NLP (lda_bad_reviews_topics.parquet).")
        return

    stt = path.stat()
    nlp_df = load_nlp_bad_reviews(str(path), int(stt.st_mtime_ns), int(stt.st_size))
    
    if nlp_df.empty:
        st.info("Không có dữ liệu đánh giá xấu.")
        return

    topic_counts = nlp_df['topic_name'].value_counts().reset_index()
    topic_counts.columns = ['topic_name', 'count']

    fig_nlp_bar = px.bar(
        topic_counts,
        x='topic_name',
        y='count',
        color='topic_name',
        title="Số lượng đánh giá tiêu cực theo nhóm nguyên nhân",
        labels={
            "topic_name": "Nhóm nguyên nhân",
            "count": "Số lượng đánh giá"
        },
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_nlp_bar.update_layout(showlegend=False, **chart_layout)
    st.plotly_chart(fig_nlp_bar, use_container_width=True)

    st.markdown("#### Khám phá Chi tiết Phản hồi Tiêu cực")

    topics = topic_counts['topic_name'].tolist()

    for topic in topics:
        count = topic_counts.loc[
            topic_counts['topic_name'] == topic, 'count'
        ].values[0]

        with st.expander(f"📌 Nhóm: {topic} ({count} đánh giá)"):
            topic_samples = nlp_df[nlp_df['topic_name'] == topic]

            sample_table = topic_samples[
                ['rating_score', 'product_name', 'seller_name', 'review_content']
            ].sample(10)

            st.dataframe(
                sample_table,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "rating_score": st.column_config.NumberColumn(
                        "⭐ Điểm",
                        format="%d/5",
                        width="small"
                    ),
                    "product_name": st.column_config.TextColumn(
                        "📦 Sản phẩm",
                        width="medium"
                    ),
                    "seller_name": st.column_config.TextColumn(
                        "🏪 Người bán",
                        width="medium"
                    ),
                    "review_content": st.column_config.TextColumn(
                        "💬 Nội dung đánh giá",
                        width="large"
                    )
                }
            )