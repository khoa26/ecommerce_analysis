"""
Imports cần thiết: import streamlit as st, import plotly.express as px, import pandas as pd, from config import COLOR_PRIMARY, và import các hàm từ data_engine.py.

Classes/Types: ChatIntent, ChatEvent.

Hàm: route_intent(query), render_assistant_event(ev, mart_filtered).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
import plotly.express as px
import streamlit as st
from config import *
from data_engine import *

ChatIntent = Literal[
    "top_categories",
    "price_distribution",
    "discount_distribution",
    "rating_distribution",
    "top_sellers",
    "compare_category_price",
    "help",
]

@dataclass(frozen=True)
class ChatEvent:
    role: Literal["user", "assistant"]
    content: str
    intent: ChatIntent | None = None
    params: dict[str, Any] | None = None


def route_intent(query: str) -> tuple[ChatIntent, dict[str, Any]]:
    q = query.strip().lower()

    if not q or any(k in q for k in ["help", "gợi ý", "hướng dẫn", "làm được gì", "có thể hỏi gì"]):
        return "help", {}

    if "ngành" in q or "danh mục" in q or "category" in q:
        if "giá" in q and ("so sánh" in q or "compare" in q or "khác nhau" in q):
            return "compare_category_price", {"n": 12}
        n = 10
        for token in q.split():
            if token.isdigit():
                n = max(3, min(30, int(token)))
                break
        return "top_categories", {"n": n}

    if any(k in q for k in ["giá", "price", "vnd"]):
        return "price_distribution", {"sample": 60_000}

    if any(k in q for k in ["khuyến mãi", "giảm", "discount", "sale"]):
        return "discount_distribution", {"sample": 60_000}

    if any(k in q for k in ["đánh giá", "rating", "sao", "review"]):
        return "rating_distribution", {"sample": 80_000}

    if any(k in q for k in ["người bán", "seller", "shop"]):
        n = 10
        for token in q.split():
            if token.isdigit():
                n = max(3, min(30, int(token)))
                break
        return "top_sellers", {"n": n}

    return "help", {}


def render_assistant_event(ev: ChatEvent, mart_filtered: pd.DataFrame) -> None:
    if ev.intent is None:
        st.markdown(ev.content)
        return

    if ev.intent == "help":
        st.markdown(
            """
        Mình có thể giúp bạn phân tích nhanh theo ngôn ngữ tự nhiên (không cần viết code), ví dụ:

        - **"Top 10 ngành hàng bán chạy nhất"**
        - **"Phân bố giá sản phẩm"** hoặc **"Giá trung bình"**
        - **"Khuyến mãi/giảm giá đang như thế nào?"**
        - **"Phân bố rating"**
        - **"Top 10 người bán theo sold"**
        - **"So sánh giá giữa các ngành hàng"**

        Bạn có thể đổi bộ lọc ở sidebar để chatbot trả lời đúng theo phạm vi bạn quan tâm.
        """
        )
        return

    if ev.intent == "top_categories":
        n = int((ev.params or {}).get("n", 10))
        df = top_categories(mart_filtered, n=n)
        st.markdown(f"**Top {n} ngành hàng theo sold (theo bộ lọc hiện tại).**")
        fig = px.bar(
            df.sort_values("sold_quantity"),
            x="sold_quantity",
            y="category_name",
            orientation="h",
            color="sold_quantity",
            color_continuous_scale="Blues",
            labels={"sold_quantity": "Số lượng đã bán", "category_name": "Ngành hàng"},
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    if ev.intent == "top_sellers":
        n = int((ev.params or {}).get("n", 10))
        df = top_sellers(mart_filtered, n=n)
        st.markdown(f"**Top {n} người bán theo sold (theo bộ lọc hiện tại).**")
        fig = px.bar(
            df.sort_values("sold_quantity"),
            x="sold_quantity",
            y="seller_name",
            orientation="h",
            color="sold_quantity",
            color_continuous_scale="Greens",
            labels={"sold_quantity": "Số lượng đã bán", "seller_name": "Người bán"},
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    if ev.intent == "price_distribution":
        sdf = mart_filtered[["current_price", "category_name"]].dropna(subset=["current_price"])
        st.markdown("**Phân bố giá (current_price) theo bộ lọc hiện tại.**")
        fig = px.histogram(
            sdf,
            x="current_price",
            nbins=60,
            color_discrete_sequence=[COLOR_PRIMARY],
            labels={"current_price": "Giá hiện tại (VND)"},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    if ev.intent == "discount_distribution":
        sdf = mart_filtered[["discount_percent"]].dropna(subset=["discount_percent"])
        st.markdown("**Phân bố mức giảm giá (discount_percent) theo bộ lọc hiện tại.**")
        fig = px.histogram(
            sdf,
            x="discount_percent",
            nbins=50,
            color_discrete_sequence=["#FFB020"],
            labels={"discount_percent": "Giảm giá (%)"},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    if ev.intent == "rating_distribution":
        sdf = mart_filtered[["review_score", "review_count"]].dropna(subset=["review_score"])
        st.markdown("**Phân bố điểm đánh giá (review_score) theo bộ lọc hiện tại.**")
        fig = px.histogram(
            sdf,
            x="review_score",
            nbins=30,
            color_discrete_sequence=["#7C3AED"],
            labels={"review_score": "Điểm đánh giá (0–5)"},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    if ev.intent == "compare_category_price":
        n = int((ev.params or {}).get("n", 12))
        if mart_filtered.empty:
            df = pd.DataFrame(columns=["category_id", "category_name", "median_price", "avg_price", "product_count"])
        else:
            df = (
                mart_filtered.groupby(["category_id", "category_name"], dropna=False)
                .agg(
                    median_price=("current_price", "median"),
                    avg_price=("current_price", "mean"),
                    product_count=("product_id", "count"),
                )
                .reset_index()
                .sort_values("product_count", ascending=False)
                .head(n)
            )
        st.markdown(f"**So sánh giá giữa {n} ngành hàng (theo số lượng sản phẩm nhiều nhất trong bộ lọc).**")
        fig = px.bar(
            df.sort_values("median_price"),
            x="median_price",
            y="category_name",
            orientation="h",
            color="product_count",
            color_continuous_scale="Teal",
            labels={"median_price": "Giá trung vị (VND)", "category_name": "Ngành hàng", "product_count": "Số sản phẩm"},
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        return

    st.markdown(ev.content)