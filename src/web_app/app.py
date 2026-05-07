from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from config import *
from data_engine import *
from chat_engine import *


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": f"{APP_TITLE} — Dashboard + Chatbot",
    },
)


st.markdown(
    f"""
<style>
  .stApp {{
    background: radial-gradient(1200px 800px at 15% 0%, rgba(26,148,255,0.18), transparent 55%),
                radial-gradient(900px 700px at 85% 10%, rgba(63,185,80,0.12), transparent 60%),
                linear-gradient(180deg, rgba(15, 18, 23, 1) 0%, rgba(12, 14, 18, 1) 100%);
  }}
  .block-container {{ padding-top: 1.25rem; padding-bottom: 2.25rem; }}
  h1, h2, h3 {{ letter-spacing: -0.02em; }}
  .muted {{ color: {COLOR_TEXT_MUTED}; }}
  .kpi-card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 14px 14px 12px 14px;
  }}
  .kpi-label {{ color: rgba(255,255,255,0.72); font-size: 0.85rem; }}
  .kpi-value {{ font-size: 1.35rem; font-weight: 700; margin-top: 2px; }}
  .kpi-sub {{ color: rgba(255,255,255,0.62); font-size: 0.8rem; margin-top: 2px; }}
  .chip {{
    display:inline-block; padding: 6px 10px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.10);
    background: rgba(255,255,255,0.04);
    margin-right: 8px; margin-bottom: 8px;
  }}
  .divider {{ height: 1px; background: rgba(255,255,255,0.08); margin: 12px 0 10px 0; }}
  .accent {{ color: {COLOR_PRIMARY}; font-weight: 700; }}
</style>
""",
    unsafe_allow_html=True,
)

def dashboard_area(mart_filtered) -> None:
    overview = compute_overview(mart_filtered)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi("Sản phẩm", fmt_int(overview["n_products"]))
    with k2:
        render_kpi("Ngành hàng", fmt_int(overview["n_categories"]))
    with k3:
        render_kpi("Người bán", fmt_int(overview["n_sellers"]))
    with k4:
        render_kpi("Tổng sold", fmt_int(overview["sold_total"]))
    with k5:
        render_kpi("Điểm TB", f"{(overview['avg_review_score'] or 0):.2f}", f"Review: {fmt_int(overview['review_total'])}")

    tabs = st.tabs(["Tổng quan", "Ngành hàng", "Giá & ưu đãi", "Người bán", "Đánh giá"])

    with tabs[0]:
        left, right = st.columns([1.2, 1])
        with left:
            df_cat = top_categories(mart_filtered, n=12)
            fig = px.bar(
                df_cat.sort_values("sold_quantity"),
                x="sold_quantity",
                y="category_name",
                orientation="h",
                color="sold_quantity",
                color_continuous_scale="Blues",
                title="Top ngành hàng theo sold",
                labels={"sold_quantity": "Số lượng đã bán", "category_name": "Ngành hàng"},
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

        with right:
            sdf = mart_filtered[["current_price", "discount_percent", "coupon_discount_amount"]].dropna(subset=["current_price"])
            fig2 = px.histogram(
                sdf,
                x="current_price",
                nbins=55,
                color_discrete_sequence=[COLOR_PRIMARY],
                title="Phân bố giá (current_price)",
                labels={"current_price": "Giá (VND)"},
            )
            fig2.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig2, width="stretch")

    with tabs[1]:
        st.markdown("### Ngành hàng")
        df_cat = top_categories(mart_filtered, n=25)
        c1, c2 = st.columns([1.1, 0.9])
        with c1:
            fig = px.bar(
                df_cat.sort_values("sold_quantity"),
                x="sold_quantity",
                y="category_name",
                orientation="h",
                color="avg_review_score",
                color_continuous_scale="Viridis",
                title="Top ngành hàng: Sold & điểm đánh giá",
                labels={
                    "sold_quantity": "Số lượng đã bán",
                    "category_name": "Ngành hàng",
                    "avg_review_score": "Điểm TB",
                },
            )
            fig.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

        with c2:
            st.dataframe(
                df_cat.assign(
                    avg_price=df_cat["avg_price"].round(0),
                    avg_review_score=df_cat["avg_review_score"].round(2),
                ).rename(
                    columns={
                        "category_name": "Ngành hàng",
                        "sold_quantity": "Sold",
                        "product_count": "Số SP",
                        "avg_review_score": "Điểm TB",
                        "avg_price": "Giá TB",
                    }
                ),
                width="stretch",
                height=520,
            )

    with tabs[2]:
        # st.markdown("### Giá & ưu đãi")
        # sdf = mart_filtered[["current_price", "original_price", "discount_percent"]].dropna(subset=["current_price"])
        # c1, c2 = st.columns(2)
        # with c1:
        #     fig = px.histogram(
        #         sdf,
        #         x="current_price",
        #         nbins=60,
        #         color_discrete_sequence=[COLOR_PRIMARY],
        #         title="Phân bố giá hiện tại",
        #         labels={"current_price": "Giá (VND)"},
        #     )
        #     fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
        #     st.plotly_chart(fig, width="stretch")

        # with c2:
        #     fig = px.histogram(
        #         sdf.dropna(subset=["discount_percent"]),
        #         x="discount_percent",
        #         nbins=50,
        #         color_discrete_sequence=["#FFB020"],
        #         title="Phân bố mức giảm giá",
        #         labels={"discount_percent": "Giảm giá (%)"},
        #     )
        #     fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
        #     st.plotly_chart(fig, width="stretch")

        # sdf2 = sdf.dropna(subset=["current_price", "discount_percent"])
        # if not sdf2.empty:
        #     fig3 = px.scatter(
        #         sdf2,
        #         x="discount_percent",
        #         y="current_price",
        #         trendline="lowess",
        #         color_discrete_sequence=["#22C55E"],
        #         title="Quan hệ giá và mức giảm",
        #         labels={"discount_percent": "Giảm giá (%)", "current_price": "Giá (VND)"},
        #     )
        #     fig3.update_traces(marker=dict(opacity=0.35, size=5))
        #     fig3.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
        #     st.plotly_chart(fig3, width="stretch")

        st.markdown("### Giá & ưu đãi")

        # =========================
        # DATA PREP
        # =========================
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

    with tabs[3]:
        st.markdown("### Người bán")
        df = top_sellers(mart_filtered, n=20)
        c1, c2 = st.columns([1.1, 0.9])
        with c1:
            fig = px.bar(
                df.sort_values("sold_quantity"),
                x="sold_quantity",
                y="seller_name",
                orientation="h",
                color="seller_rating",
                color_continuous_scale="YlGn",
                title="Top người bán theo sold & rating",
                labels={"sold_quantity": "Số lượng đã bán", "seller_name": "Người bán", "seller_rating": "Rating"},
            )
            fig.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

        with c2:
            st.dataframe(
                df.assign(seller_rating=df["seller_rating"].round(2)).rename(
                    columns={
                        "seller_name": "Người bán",
                        "sold_quantity": "Sold",
                        "product_count": "Số SP",
                        "seller_rating": "Rating",
                    }
                ),
                width="stretch",
                height=520,
            )

    with tabs[4]:
        st.markdown("### Đánh giá")
        sdf = mart_filtered[["review_score", "review_count"]].dropna(subset=["review_score"])
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.histogram(
                sdf,
                x="review_score",
                nbins=30,
                color_discrete_sequence=["#7C3AED"],
                title="Phân bố điểm đánh giá (review_score)",
                labels={"review_score": "Điểm (0–5)"},
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, width="stretch")

        with c2:
            sdf2 = sdf.dropna(subset=["review_count"])
            if not sdf2.empty:
                fig2 = px.scatter(
                    sdf2,
                    x="review_count",
                    y="review_score",
                    trendline="lowess",
                    color_discrete_sequence=["#A78BFA"],
                    title="Điểm vs số lượt review",
                    labels={"review_count": "Số lượt review", "review_score": "Điểm"},
                )
                fig2.update_traces(marker=dict(opacity=0.35, size=5))
                fig2.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig2, width="stretch")

def chatbot_area(mart_filtered: pd.DataFrame) -> None:
    st.markdown("### 🤖 Chatbot phân tích")
    st.caption("Nhập câu hỏi bằng tiếng Việt. Chatbot sẽ trả lời theo dữ liệu và bộ lọc hiện tại.")

    st.markdown(
        """
        <span class="chip">Gợi ý:</span>
        <span class="chip">Top ngành hàng</span>
        <span class="chip">Phân bố giá</span>
        <span class="chip">Khuyến mãi</span>
        <span class="chip">Rating</span>
        <span class="chip">Top người bán</span>
        """,
        unsafe_allow_html=True,
    )

    for ev in st.session_state.chat_events:
        with st.chat_message(ev.role):
            if ev.role == "assistant":
                render_assistant_event(ev, mart_filtered)
            else:
                st.markdown(ev.content)

    prompt = st.chat_input("Ví dụ: Top 10 ngành hàng bán chạy nhất")
    if prompt:
        st.session_state.chat_events.append(ChatEvent(role="user", content=prompt))
        intent, params = route_intent(prompt)

        if intent == "help":
            content = "Mình gợi ý một vài câu hỏi phổ biến để bạn bắt đầu."
        elif intent == "top_categories":
            content = "Mình đang tổng hợp top ngành hàng theo sold."
        elif intent == "top_sellers":
            content = "Mình đang tổng hợp top người bán theo sold."
        elif intent == "price_distribution":
            content = "Mình đang tổng hợp phân bố giá hiện tại."
        elif intent == "discount_distribution":
            content = "Mình đang tổng hợp phân bố mức giảm giá."
        elif intent == "rating_distribution":
            content = "Mình đang tổng hợp phân bố điểm đánh giá."
        elif intent == "compare_category_price":
            content = "Mình đang so sánh giá giữa các ngành hàng."
        else:
            content = "Mình đang phân tích yêu cầu của bạn."

        st.session_state.chat_events.append(
            ChatEvent(role="assistant", content=content, intent=intent, params=params)
        )
        st.rerun()

def main() -> None:
    st.markdown(f"## {APP_TITLE}")
    st.markdown(
        "<span class='muted'>Dashboard tổng quan thị trường TMĐT (Tiki) + Chatbot tương tác dựa trên dữ liệu trong <span class='accent'>data/processed</span>.</span>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("## Điều hướng")

    st.sidebar.markdown("## Bộ lọc dữ liệu")

    try:
        mart = build_product_mart()
    except Exception as e:
        st.error(f"Can not load data from {PROCESSED_DIR}.")
        st.code(str(e))
        st.info(f"Suggestion: make sure you have the following files in {PROCESSED_DIR}")
        return

    categories_df = load_tables()["category"].copy()

    # ép kiểu
    categories_df["category_id"] = pd.to_numeric(categories_df["category_id"], errors="coerce")
    categories_df["parent_category_id"] = pd.to_numeric(categories_df["parent_category_id"], errors="coerce")
    categories_df["level"] = pd.to_numeric(categories_df["level"], errors="coerce")

    # 👉 1. category có product
    valid_ids = set(mart["category_id"].dropna().unique())

    # 👉 2. lấy toàn bộ ancestor (cha, ông...)
    def get_all_parents(category_df, child_ids):
        parents = set()
        current = set(child_ids)

        while True:
            new_parents = set(
                category_df.loc[
                    category_df["category_id"].isin(current),
                    "parent_category_id"
                ].dropna()
            )

            new_parents = new_parents - parents
            if not new_parents:
                break

            parents.update(new_parents)
            current = new_parents

        return parents

    parent_ids = get_all_parents(categories_df, valid_ids)

    # 👉 3. giữ category có product hoặc là cha của nó
    keep_ids = valid_ids.union(parent_ids)

    categories_df2 = categories_df[
        categories_df["category_id"].isin(keep_ids)
    ]

    # 👉 4. chỉ lấy level 1–2
    categories_df2 = categories_df2[categories_df2["level"].isin([1, 2])]
    exclude_categories = ["Điện Tử - Điện Lạnh"]

    categories_df2 = categories_df2[
        ~categories_df2["category_name"].isin(exclude_categories)
    ]

    # 👉 5. sort đẹp
    categories_df2 = categories_df2.sort_values(["level", "category_name"])

    # 👉 6. tạo options (indent theo level cho dễ nhìn)
    category_options = ["Tất cả ngành hàng"] + [
        f"{'  ' * (int(row.level)-1)}{row.category_name}"
        for _, row in categories_df2.iterrows()
    ]

    # 👉 mapping để lấy id
    category_map = {
        f"{'  ' * (int(row.level)-1)}{row.category_name}": row.category_id
        for _, row in categories_df2.iterrows()
    }

    category_name = st.sidebar.selectbox("Ngành hàng", category_options, index=0)

    category_id = None
    if category_name != "Tất cả ngành hàng":
        category_id = category_map.get(category_name)

    current_price_num = pd.to_numeric(mart.get("current_price"), errors="coerce")
    max_slider_val = int(current_price_num.quantile(0.98) or 0)
    max_limit = int(max_slider_val * 1.2)
    min_slider_val = int(current_price_num.dropna().min() or 0)

    price_min, price_max = st.sidebar.slider(
        "Khoảng giá (VND)",
        min_value=min_slider_val,
        max_value=max_limit,
        value=(min_slider_val, max_slider_val),
        step=10000,
        format="%d ₫"
    )
    price_min, price_max = float(price_min), float(price_max)

    max_sold = int(mart["sold_quantity"].quantile(0.99) or 0)
    sold_min = int(
        st.sidebar.slider(
            "Sold tối thiểu",
            min_value=0,
            max_value=max_sold,
            value=0,
            step=1
        )
    )

    mart_filtered = apply_filters(mart, category_id, price_min, price_max, sold_min, categories_df)

    st.sidebar.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.sidebar.caption(f"Dòng sản phẩm sau lọc: **{fmt_int(len(mart_filtered))}** / {fmt_int(len(mart))}")

    if "chat_events" not in st.session_state:
        st.session_state.chat_events = [
            ChatEvent(
                role="assistant",
                content="Bạn muốn phân tích gì từ dữ liệu Tiki? Mình có thể trả lời bằng số liệu và biểu đồ.",
                intent="help",
                params={},
            )
        ]

    dashboard_area(mart_filtered)
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    chatbot_area(mart_filtered)

    st.markdown(
        f"<div class='muted'>Cập nhật lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()