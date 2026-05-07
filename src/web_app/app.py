from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "Hệ thống trực quan hóa dữ liệu TMĐT Tiki"

COLOR_PRIMARY = "#1A94FF"  # Tiki blue-ish
COLOR_TEXT_MUTED = "rgba(255,255,255,.7)"


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


ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


@st.cache_data(show_spinner=False)
def _read_parquet(path: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(path, columns=columns)


@st.cache_data(show_spinner=False)
def load_tables() -> dict[str, pd.DataFrame]:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu: {PROCESSED_DIR}")

    required = [
        "product.parquet",
        "category.parquet",
        "seller.parquet",
        "price_offer.parquet",
    ]
    missing = [name for name in required if not (PROCESSED_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Thiếu file trong data/processed: {', '.join(missing)}")

    product = _read_parquet(
        str(PROCESSED_DIR / "product.parquet"),
        columns=[
            "product_id",
            "product_name",
            "short_description",
            "category_id",
            "seller_id",
            "product_url",
            "image_url",
            "author_brand",
            "sold_quantity",
            "review_count",
            "review_score",
        ],
    )
    category = _read_parquet(
        str(PROCESSED_DIR / "category.parquet"),
        columns=["category_id", "category_name", "parent_category_id", "level", "category_path", "category_url"],
    )
    seller = _read_parquet(
        str(PROCESSED_DIR / "seller.parquet"),
        columns=["seller_id", "seller_name", "seller_rating", "total_reviews"],
    )
    price_offer = _read_parquet(
        str(PROCESSED_DIR / "price_offer.parquet"),
        columns=["product_id", "current_price", "original_price", "discount_percent", "crawl_time", "offer_id"],
    )

    return {
        "product": product,
        "category": category,
        "seller": seller,
        "price_offer": price_offer,
    }


@st.cache_data(show_spinner=False)
def build_product_mart() -> pd.DataFrame:
    t = load_tables()

    product = t["product"]
    category = t["category"][["category_id", "category_name", "parent_category_id", "level"]].copy()
    seller = t["seller"]

    price_offer = t["price_offer"].copy()
    price_offer["crawl_time_dt"] = pd.to_datetime(price_offer["crawl_time"], errors="coerce")
    price_offer = price_offer.sort_values(["product_id", "crawl_time_dt"], kind="mergesort")
    latest_price = price_offer.drop_duplicates(subset=["product_id"], keep="last")[
        ["product_id", "current_price", "original_price", "discount_percent", "crawl_time_dt"]
    ].rename(columns={"crawl_time_dt": "last_crawl_time"})

    mart = (
        product.merge(category, on="category_id", how="left")
        .merge(seller, on="seller_id", how="left")
        .merge(latest_price, on="product_id", how="left")
    )

    for col in ["sold_quantity", "review_count", "review_score", "current_price", "original_price", "discount_percent"]:
        if col in mart.columns:
            mart[col] = pd.to_numeric(mart[col], errors="coerce")

    return mart


def vnd(x: float | int | None) -> str:
    if x is None:
        return "—"
    try:
        return f"{int(round(float(x))):,} ₫".replace(",", ".")
    except Exception:
        return "—"


def pct(x: float | None, digits: int = 1) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.{digits}f}%"
    except Exception:
        return "—"


def fmt_int(x: float | int | None) -> str:
    if x is None:
        return "—"
    try:
        return f"{int(round(float(x))):,}".replace(",", ".")
    except Exception:
        return "—"


def render_kpi(label: str, value: str, sub: str | None = None) -> None:
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"""
<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {sub_html}
</div>
""",
        unsafe_allow_html=True,
    )


def sample_pd(mart: pd.DataFrame, columns: list[str], n: int = 50_000) -> pd.DataFrame:
    cols = [c for c in columns if c in mart.columns]
    if not cols or mart.empty:
        return pd.DataFrame()
    take = min(n, len(mart))
    return mart.loc[:, cols].sample(n=take, replace=False, random_state=7)


def top_categories(mart: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if mart.empty:
        return pd.DataFrame(columns=["category_id", "category_name", "sold_quantity", "product_count", "avg_review_score", "avg_price"])
    df = (
        mart.groupby(["category_id", "category_name"], dropna=False)
        .agg(
            sold_quantity=("sold_quantity", "sum"),
            product_count=("product_id", "count"),
            avg_review_score=("review_score", "mean"),
            avg_price=("current_price", "mean"),
        )
        .reset_index()
        .sort_values("sold_quantity", ascending=False)
        .head(n)
    )
    return df


def top_sellers(mart: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if mart.empty:
        return pd.DataFrame(columns=["seller_id", "seller_name", "sold_quantity", "product_count", "seller_rating"])
    df = (
        mart.groupby(["seller_id", "seller_name"], dropna=False)
        .agg(
            sold_quantity=("sold_quantity", "sum"),
            product_count=("product_id", "count"),
            seller_rating=("seller_rating", "mean"),
        )
        .reset_index()
        .sort_values("sold_quantity", ascending=False)
        .head(n)
    )
    return df


def compute_overview(mart: pd.DataFrame) -> dict[str, float]:
    if mart.empty:
        return {
            "n_products": 0.0,
            "n_categories": 0.0,
            "n_sellers": 0.0,
            "sold_total": 0.0,
            "review_total": 0.0,
            "avg_review_score": 0.0,
            "avg_current_price": 0.0,
            "avg_discount": 0.0,
        }

    return {
        "n_products": float(mart["product_id"].nunique(dropna=True)),
        "n_categories": float(mart["category_id"].nunique(dropna=True)),
        "n_sellers": float(mart["seller_id"].nunique(dropna=True)),
        "sold_total": float(pd.to_numeric(mart["sold_quantity"], errors="coerce").fillna(0).sum()),
        "review_total": float(pd.to_numeric(mart["review_count"], errors="coerce").fillna(0).sum()),
        "avg_review_score": float(pd.to_numeric(mart["review_score"], errors="coerce").dropna().mean() or 0.0),
        "avg_current_price": float(pd.to_numeric(mart["current_price"], errors="coerce").dropna().mean() or 0.0),
        "avg_discount": float(pd.to_numeric(mart["discount_percent"], errors="coerce").dropna().mean() or 0.0),
    }


def apply_filters(
    mart: pd.DataFrame,
    category_id: int | None,
    price_min: float | None,
    price_max: float | None,
    sold_min: int,
) -> pd.DataFrame:
    out = mart
    if category_id is not None:
        out = out.loc[out["category_id"] == category_id]
    if price_min is not None and price_max is not None:
        out = out.loc[out["current_price"].between(price_min, price_max, inclusive="both")]
    if sold_min > 0:
        out = out.loc[out["sold_quantity"] >= sold_min]
    return out


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
        sample_n = int((ev.params or {}).get("sample", 60_000))
        sdf = sample_pd(mart_filtered, ["current_price", "category_name"], n=sample_n)
        sdf = sdf.dropna(subset=["current_price"])
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
        sample_n = int((ev.params or {}).get("sample", 60_000))
        sdf = sample_pd(mart_filtered, ["discount_percent"], n=sample_n)
        sdf = sdf.dropna(subset=["discount_percent"])
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
        sample_n = int((ev.params or {}).get("sample", 80_000))
        sdf = sample_pd(mart_filtered, ["review_score", "review_count"], n=sample_n)
        sdf = sdf.dropna(subset=["review_score"])
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


def main() -> None:
    st.markdown(f"## {APP_TITLE}")
    st.markdown(
        "<span class='muted'>Dashboard tổng quan thị trường TMĐT (Tiki) + Chatbot tương tác dựa trên dữ liệu trong <span class='accent'>data/processed</span>.</span>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("## Điều hướng")
    layout_mode = st.sidebar.radio(
        "Bố cục",
        ["Dashboard + Chatbot (bên cạnh)", "Dashboard + Chatbot (bên dưới)"],
        index=0,
    )

    st.sidebar.markdown("## Bộ lọc dữ liệu")

    try:
        mart = build_product_mart()
    except Exception as e:
        st.error("Không thể tải dữ liệu từ `data/processed`.")
        st.code(str(e))
        st.info(
            "Gợi ý: đảm bảo bạn có các file Parquet trong `data/processed` như `product.parquet`, `category.parquet`, `seller.parquet`, `price_offer.parquet`."
        )
        return

    categories_df = load_tables()["category"][["category_id", "category_name", "level"]].copy()
    categories_df = categories_df.sort_values(["level", "category_name"])

    category_options = ["Tất cả ngành hàng"] + categories_df["category_name"].fillna("—").tolist()
    category_name = st.sidebar.selectbox("Ngành hàng", category_options, index=0)
    category_id: int | None = None
    if category_name != "Tất cả ngành hàng":
        row = categories_df.loc[categories_df["category_name"] == category_name].head(1)
        if len(row) > 0:
            category_id = int(row["category_id"].iloc[0])

    current_price_num = pd.to_numeric(mart.get("current_price"), errors="coerce")
    min_price = float(current_price_num.dropna().min() or 0.0)
    max_price = float(current_price_num.dropna().max() or 0.0)
    if max_price <= 0:
        price_min, price_max = None, None
        st.sidebar.caption("Không có dữ liệu giá hợp lệ để lọc.")
    else:
        pmin_default, pmax_default = min_price, max_price
        price_min, price_max = st.sidebar.slider(
            "Khoảng giá (VND)",
            min_value=0,
            max_value=int(max_price),
            value=(int(pmin_default), int(pmax_default)),
            step=max(1_000, int(max_price // 200) if max_price else 1_000),
        )
        price_min, price_max = float(price_min), float(price_max)

    sold_min = int(
        st.sidebar.slider(
            "Sold tối thiểu",
            min_value=0,
            max_value=50_000,
            value=0,
            step=100,
        )
    )

    mart_filtered = apply_filters(mart, category_id, price_min, price_max, sold_min)

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

    def dashboard_area() -> None:
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
                sdf = sample_pd(mart_filtered, ["current_price", "discount_percent"], n=50_000).dropna(
                    subset=["current_price"]
                )
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
            st.markdown("### Giá & ưu đãi")
            sdf = sample_pd(mart_filtered, ["current_price", "original_price", "discount_percent"], n=70_000)
            c1, c2 = st.columns(2)
            with c1:
                fig = px.histogram(
                    sdf.dropna(subset=["current_price"]),
                    x="current_price",
                    nbins=60,
                    color_discrete_sequence=[COLOR_PRIMARY],
                    title="Phân bố giá hiện tại",
                    labels={"current_price": "Giá (VND)"},
                )
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, width="stretch")

            with c2:
                fig = px.histogram(
                    sdf.dropna(subset=["discount_percent"]),
                    x="discount_percent",
                    nbins=50,
                    color_discrete_sequence=["#FFB020"],
                    title="Phân bố mức giảm giá",
                    labels={"discount_percent": "Giảm giá (%)"},
                )
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig, width="stretch")

            sdf2 = sdf.dropna(subset=["current_price", "discount_percent"])
            if not sdf2.empty:
                fig3 = px.scatter(
                    sdf2.sample(n=min(25_000, len(sdf2)), random_state=7),
                    x="discount_percent",
                    y="current_price",
                    color_discrete_sequence=["#22C55E"],
                    title="Quan hệ giá và mức giảm",
                    labels={"discount_percent": "Giảm giá (%)", "current_price": "Giá (VND)"},
                )
                fig3.update_traces(marker=dict(opacity=0.35, size=5))
                fig3.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig3, width="stretch")

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
            sdf = sample_pd(mart_filtered, ["review_score", "review_count"], n=90_000).dropna(subset=["review_score"])
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
                        sdf2.sample(n=min(30_000, len(sdf2)), random_state=11),
                        x="review_count",
                        y="review_score",
                        color_discrete_sequence=["#A78BFA"],
                        title="Điểm vs số lượt review",
                        labels={"review_count": "Số lượt review", "review_score": "Điểm"},
                    )
                    fig2.update_traces(marker=dict(opacity=0.35, size=5))
                    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
                    st.plotly_chart(fig2, width="stretch")

    def chatbot_area() -> None:
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

    if layout_mode == "Dashboard + Chatbot (bên cạnh)":
        left, right = st.columns([2.2, 1.0], gap="large")
        with left:
            dashboard_area()
        with right:
            chatbot_area()
    else:
        dashboard_area()
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        chatbot_area()

    st.markdown(
        f"<div class='muted'>Cập nhật lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()