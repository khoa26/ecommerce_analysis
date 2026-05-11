"""
Imports cần thiết: import pandas as pd, import streamlit as st (để dùng @st.cache_data), from config import PROCESSED_DIR.

Hàm cốt lõi: _read_parquet, load_tables, build_product_mart, apply_filters.

Hàm phân tích: sample_pd, top_categories, top_sellers, compute_overview.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import numpy as np
import re
from pathlib import Path
from config import PROCESSED_DIR

REQUIRED_PARQUETS: list[str] = [
    "category.parquet",
    "coupon.parquet",
    "offer_coupon.parquet",
    "offer_service.parquet",
    "price_offer.parquet",
    "product.parquet",
    "review.parquet",
    "reviewer.parquet",
    "seller.parquet",
    "service.parquet",
]

def get_processed_signature(
    required: list[str] = REQUIRED_PARQUETS,
    extra_paths: list[Path] | None = None,
) -> tuple[tuple[str, int, int], ...]:
    """
    Tạo chữ ký dữ liệu dựa trên (tên file, mtime_ns, size).
    Khi bất kỳ file nào thay đổi, chữ ký đổi -> cache invalidation.
    """
    items: list[tuple[str, int, int]] = []

    for name in required:
        p = PROCESSED_DIR / name
        try:
            stt = p.stat()
            items.append((name, int(stt.st_mtime_ns), int(stt.st_size)))
        except FileNotFoundError:
            items.append((name, 0, 0))

    if extra_paths:
        for p in extra_paths:
            key = str(p)
            try:
                stt = p.stat()
                items.append((key, int(stt.st_mtime_ns), int(stt.st_size)))
            except FileNotFoundError:
                items.append((key, 0, 0))

    items.sort(key=lambda x: x[0])
    return tuple(items)

@st.cache_data(show_spinner=False)
def read_parquet(
    path: str,
    columns: list[str] | None = None,
    mtime_ns: int | None = None,
    size: int | None = None,
) -> pd.DataFrame:
    return pd.read_parquet(path, columns=columns)

@st.cache_data(show_spinner=False)
def _load_tables_cached(data_sig: tuple[tuple[str, int, int], ...]) -> dict[str, pd.DataFrame]:
    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Could not find data directory: {PROCESSED_DIR}")

    sig_map = {name: (mtime_ns, size) for name, mtime_ns, size in data_sig}

    missing = [name for name in REQUIRED_PARQUETS if not (PROCESSED_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing files in {PROCESSED_DIR}: {', '.join(missing)}")

    tables = {}
    for name in REQUIRED_PARQUETS:
        mtime_ns, size = sig_map.get(name, (None, None))
        df = read_parquet(str(PROCESSED_DIR / name), mtime_ns=mtime_ns, size=size)
        tables[name.replace(".parquet", "")] = df

    return tables

def load_tables(data_sig: tuple[tuple[str, int, int], ...] | None = None) -> dict[str, pd.DataFrame]:
    sig = data_sig or get_processed_signature()
    return _load_tables_cached(sig)

def extract_coupon_rules(df_coupon: pd.DataFrame) -> pd.DataFrame:
    """
    Hàm phụ trợ để bóc tách quy tắc giảm giá từ cột title.
    - Rút % giảm giá (ví dụ: "8%" -> 0.08)
    - Rút số tiền K tối đa/cố định (ví dụ: "50K" -> 50000)
    """
    df = df_coupon.copy()
    
    # Rút trích % giảm giá (tìm số đứng ngay trước dấu %)
    rate_str = df['title'].str.extract(r'(\d+(?:\.\d+)?)%')[0]
    df['discount_rate'] = pd.to_numeric(rate_str, errors='coerce').fillna(0) / 100
    
    # Rút trích số tiền K (tìm số đứng ngay trước chữ 'k' hoặc 'K')
    amt_str = df['title'].str.extract(r'(\d+(?:\.\d+)?)\s*[kK]')[0]
    df['max_discount_amount'] = pd.to_numeric(amt_str, errors='coerce').fillna(0) * 1000
    
    return df

# @st.cache_data(show_spinner=False)
# def build_product_mart() -> pd.DataFrame:
#     tables = load_tables()

#     product = tables["product"]
#     category = tables["category"]
#     seller = tables["seller"]

#     price_offer = tables["price_offer"]
#     price_offer["crawl_time_dt"] = pd.to_datetime(price_offer["crawl_time"], errors="coerce")
#     price_offer = price_offer.sort_values(["product_id", "crawl_time_dt"], kind="mergesort")
#     latest_price = price_offer.drop_duplicates(subset=["product_id"], keep="last")[
#         ["product_id", "offer_id", "current_price", "original_price", "discount_percent", "crawl_time_dt"]
#     ].rename(columns={"crawl_time_dt": "last_crawl_time"})

#     offer_coupon = tables["offer_coupon"]
#     coupon = extract_coupon_rules(tables["coupon"])
#     coupon_link = offer_coupon.merge(
#         coupon[["coupon_id", "discount_rate", "max_discount_amount"]], 
#         on="coupon_id", 
#         how="inner"
#     )
    
#     price_with_coupons = latest_price[["product_id", "offer_id", "current_price"]].merge(
#         coupon_link, 
#         on="offer_id", 
#         how="inner"
#     )

#     calc_discount = np.where(
#         price_with_coupons["discount_rate"] > 0,
#         np.minimum(
#             price_with_coupons["current_price"] * price_with_coupons["discount_rate"], 
#             price_with_coupons["max_discount_amount"]
#         ),
#         price_with_coupons["max_discount_amount"]
#     )
#     price_with_coupons["actual_coupon_value"] = calc_discount
    
#     best_coupons = price_with_coupons.groupby("product_id")["actual_coupon_value"].max().reset_index()
#     best_coupons = best_coupons.rename(columns={"actual_coupon_value": "coupon_discount_amount"})
    
#     latest_price = latest_price.merge(best_coupons, on="product_id", how="left")
#     latest_price["coupon_discount_amount"] = latest_price["coupon_discount_amount"].fillna(0)
#     latest_price["has_coupon"] = latest_price["coupon_discount_amount"] > 0

#     mart = (
#         product.merge(category, on="category_id", how="left")
#         .merge(seller, on="seller_id", how="left")
#         .merge(latest_price, on="product_id", how="left")
#     )

#     numeric_cols = [
#         "sold_quantity", "review_count", "review_score", 
#         "current_price", "original_price", "discount_percent", 
#         "coupon_discount_amount"
#     ]
#     for col in numeric_cols:
#         if col in mart.columns:
#             mart[col] = pd.to_numeric(mart[col], errors="coerce")

#     return mart

@st.cache_data(show_spinner=False)
def _build_mart_cached(data_sig: tuple[tuple[str, int, int], ...]) -> pd.DataFrame:
    tables = _load_tables_cached(data_sig)

    # =============================
    # LOAD TABLES
    # =============================
    product = tables["product"]
    category = tables["category"]
    seller = tables["seller"]
    review = tables["review"]

    price_offer = tables["price_offer"]
    offer_coupon = tables["offer_coupon"]
    coupon = extract_coupon_rules(tables["coupon"])

    offer_service = tables["offer_service"]
    service = tables["service"]

    # =============================
    # FIX DATA TYPES (CRITICAL)
    # =============================
    for df in [product, price_offer, review]:
        df["product_id"] = df["product_id"].astype(str)

    seller["seller_id"] = seller["seller_id"].astype(str)
    product["seller_id"] = product["seller_id"].astype(str)

    # =============================
    # PRICE: LẤY GIÁ MỚI NHẤT
    # =============================
    price_offer["crawl_time_dt"] = pd.to_datetime(price_offer["crawl_time"], errors="coerce")

    latest_price = (
        price_offer
        .sort_values(["product_id", "crawl_time_dt"])
        .drop_duplicates("product_id", keep="last")
    )

    latest_price = latest_price[
        ["product_id", "offer_id", "current_price", "original_price", "discount_percent", "crawl_time_dt"]
    ].rename(columns={"crawl_time_dt": "last_crawl_time"})

    # =============================
    # COUPON
    # =============================
    coupon_link = offer_coupon.merge(
        coupon[["coupon_id", "discount_rate", "max_discount_amount"]],
        on="coupon_id",
        how="left"
    )

    price_coupon = latest_price.merge(coupon_link, on="offer_id", how="left")

    price_coupon["actual_coupon_value"] = np.where(
        price_coupon["discount_rate"] > 0,
        np.minimum(
            price_coupon["current_price"] * price_coupon["discount_rate"],
            price_coupon["max_discount_amount"]
        ),
        price_coupon["max_discount_amount"]
    )

    best_coupon = (
        price_coupon.groupby("product_id")["actual_coupon_value"]
        .max()
        .reset_index()
        .rename(columns={"actual_coupon_value": "coupon_discount_amount"})
    )

    latest_price = latest_price.merge(best_coupon, on="product_id", how="left")
    latest_price["coupon_discount_amount"] = latest_price["coupon_discount_amount"].fillna(0)
    latest_price["has_coupon"] = latest_price["coupon_discount_amount"] > 0

    # =============================
    # REVIEW AGG (QUAN TRỌNG)
    # =============================
    review["rating_score"] = pd.to_numeric(review["rating_score"], errors="coerce")

    review_agg = (
        review.groupby("product_id")
        .agg(
            review_count_real=("rating_score", "count"),
            review_score_real=("rating_score", "mean"),
            bad_review_count=("rating_score", lambda x: (x <= 2).sum())
        )
        .reset_index()
    )

    # =============================
    # SERVICE (OPTIONAL)
    # =============================
    service_map = offer_service.merge(service, on="service_id", how="left")

    service_agg = (
        service_map.groupby("offer_id")["service_name"]
        .apply(lambda x: ", ".join(x.dropna().unique()))
        .reset_index()
    )

    latest_price = latest_price.merge(service_agg, on="offer_id", how="left")

    # =============================
    # BUILD MART
    # =============================
    mart = (
        product
        .merge(category, on="category_id", how="left")
        .merge(seller, on="seller_id", how="left")
        .merge(latest_price, on="product_id", how="left")
        .merge(review_agg, on="product_id", how="left")
    )

    # =============================
    # CLEAN NUMERIC
    # =============================
    numeric_cols = [
        "sold_quantity", "review_count", "review_score",
        "review_count_real", "review_score_real",
        "current_price", "original_price",
        "discount_percent", "coupon_discount_amount"
    ]

    for col in numeric_cols:
        if col in mart.columns:
            mart[col] = pd.to_numeric(mart[col], errors="coerce")

    # =============================
    # FIX REVIEW SCORE BUG 🔥
    # =============================
    mart["review_score_real"] = mart["review_score_real"].clip(0, 5)
    # =============================
    # RATING ALIAS - TÁCH RÕ 3 LOẠI RATING
    # =============================

    # Rating gốc nằm trong bảng product
    mart["product_rating"] = pd.to_numeric(
        mart["review_score"],
        errors="coerce"
    ).clip(0, 5)

    # Rating tính từ bảng review
    mart["review_rating"] = pd.to_numeric(
        mart["review_score_real"],
        errors="coerce"
    ).clip(0, 5)

    # Rating của seller
    if "seller_rating" in mart.columns:
        mart["seller_rating_clean"] = pd.to_numeric(
            mart["seller_rating"],
            errors="coerce"
        ).clip(0, 5)
    else:
        mart["seller_rating_clean"] = np.nan

    # Doanh thu ước tính
    mart["estimated_revenue"] = (
        pd.to_numeric(mart["current_price"], errors="coerce").fillna(0)
        * pd.to_numeric(mart["sold_quantity"], errors="coerce").fillna(0)
    )

    # Cờ discount để dashboard dùng
    mart["has_discount"] = (
        pd.to_numeric(mart["discount_percent"], errors="coerce").fillna(0) > 0
    )

    # Đảm bảo has_coupon tồn tại
    if "has_coupon" not in mart.columns:
        mart["has_coupon"] = (
            pd.to_numeric(mart["coupon_discount_amount"], errors="coerce").fillna(0) > 0
        )

    return mart

def build_mart(data_sig: tuple[tuple[str, int, int], ...] | None = None) -> pd.DataFrame:
    sig = data_sig or get_processed_signature()
    return _build_mart_cached(sig)

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
            "avg_rating_score": 0.0,
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
        "avg_rating_score": float(pd.to_numeric(mart["review_score_real"], errors="coerce").dropna().mean() or 0.0),
        "avg_current_price": float(pd.to_numeric(mart["current_price"], errors="coerce").dropna().mean() or 0.0),
        "avg_discount": float(pd.to_numeric(mart["discount_percent"], errors="coerce").dropna().mean() or 0.0),
    }

def get_category_descendants(category_df, parent_id):
    children = category_df[category_df["parent_category_id"] == parent_id]["category_id"].tolist()
    
    all_ids = [parent_id]
    for child in children:
        all_ids.extend(get_category_descendants(category_df, child))
    
    return all_ids

def apply_filters(
    mart: pd.DataFrame,
    category_id: int | None,
    price_min: float | None,
    price_max: float | None,
    sold_min: int,
    category_df: pd.DataFrame,
) -> pd.DataFrame:

    out = mart

    if category_id is not None:
        category_ids = get_category_descendants(category_df, category_id)
        out = out.loc[out["category_id"].isin(category_ids)]

    if price_min is not None and price_max is not None:
        out = out.loc[out["current_price"].between(price_min, price_max)]

    if sold_min > 0:
        out = out.loc[out["sold_quantity"] >= sold_min]

    return out