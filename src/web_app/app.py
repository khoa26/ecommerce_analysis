from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
from config import *
from data_engine import *
from chat_engine import *
from components.price_discount import render_price_discount_tab
from components.overview import render_overview_tab
from components.category import render_category_tab
from components.seller import render_seller_tab
from components.review import render_review_tab


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

def dashboard_area(mart_filtered, price_offer) -> None:
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
        render_kpi("Điểm TB", f"{(overview['avg_rating_score'] or 0):.2f}/5")

    tabs = st.tabs(["Tổng quan", "Ngành hàng", "Giá & ưu đãi", "Người bán", "Đánh giá", "Trợ lý AI"])

    with tabs[0]:
        render_overview_tab(mart_filtered)

    with tabs[1]:
        render_category_tab(mart_filtered)

    with tabs[2]:
        render_price_discount_tab(mart_filtered, price_offer)

    with tabs[3]:
        render_seller_tab(mart_filtered)
        
    with tabs[4]:
        render_review_tab(mart_filtered)

    with tabs[5]:
        chatbot_area(mart_filtered)


def main() -> None:
    st.markdown(f"## {APP_TITLE}")
    st.markdown(
        "<span class='muted'>Dashboard tổng quan thị trường TMĐT (Tiki) + Chatbot tương tác",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("## Bộ lọc dữ liệu")
    if st.sidebar.button("Tải lại", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    try:
        data_sig = get_processed_signature()
        mart = build_mart(data_sig)
        price_offer = load_tables(data_sig)["price_offer"].copy()
    except Exception as e:
        st.error(f"Can not load data from {PROCESSED_DIR}.")
        st.code(str(e))
        st.info(f"Suggestion: make sure you have the following files in {PROCESSED_DIR}")
        return

    categories_df = load_tables(data_sig)["category"].copy()

    categories_df["category_id"] = pd.to_numeric(categories_df["category_id"], errors="coerce")
    categories_df["parent_category_id"] = pd.to_numeric(categories_df["parent_category_id"], errors="coerce")
    categories_df["level"] = pd.to_numeric(categories_df["level"], errors="coerce")

    valid_ids = set(mart["category_id"].dropna().unique())

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

    keep_ids = valid_ids.union(parent_ids)

    categories_df2 = categories_df[
        categories_df["category_id"].isin(keep_ids)
    ]

    categories_df2 = categories_df2[categories_df2["level"].isin([1, 2])]
    exclude_categories = ["Điện Tử - Điện Lạnh"]

    categories_df2 = categories_df2[
        ~categories_df2["category_name"].isin(exclude_categories)
    ]

    categories_df2 = categories_df2.sort_values(["level", "category_name"])

    category_options = ["Tất cả ngành hàng"] + [
        f"{'  ' * (int(row.level)-1)}{row.category_name}"
        for _, row in categories_df2.iterrows()
    ]

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
                type="text",
                content="Chào bạn! Bạn muốn phân tích gì từ dữ liệu Tiki? Mình có thể hỗ trợ sinh mã Python và vẽ biểu đồ trực tiếp nhé."
            )
        ]

    dashboard_area(mart_filtered, price_offer)

    st.markdown(
        f"<div class='muted'>Cập nhật lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()