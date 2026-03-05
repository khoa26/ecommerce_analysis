import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
from supabase import create_client, Client

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

USER = os.getenv("LOCAL_DB_USER")
PASSWORD = os.getenv("LOCAL_DB_PASS")
HOST = os.getenv("LOCAL_DB_HOST")
DBNAME = os.getenv("LOCAL_DB_NAME")
PORT = os.getenv("LOCAL_DB_PORT")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BATCH_SIZE = int(os.getenv("UPLOAD_BATCH_SIZE", "1000"))

# Sắp xếp đúng thứ tự Foreign Key (Cha đẩy trước, Con đẩy sau)
TABLE_ORDER = [
    "category",      # Độc lập (tự tham chiếu)
    "seller",        # Độc lập
    "service",       # Độc lập
    "coupon",        # Độc lập
    "reviewer",      # Độc lập
    "product",       # Phụ thuộc category, seller
    "price_offer",   # Phụ thuộc product
    "offer_service", # Phụ thuộc price_offer, service
    "offer_coupon",  # Phụ thuộc price_offer, coupon
    "review",        # Phụ thuộc product, reviewer
]

# Định nghĩa Primary Keys (bao gồm cả Composite Keys cho bảng trung gian)
PRIMARY_KEYS = {
    "category": "category_id",
    "seller": "seller_id",
    "service": "service_id",
    "coupon": "coupon_id",
    "reviewer": "reviewer_id",
    "product": "product_id",
    "price_offer": "offer_id",
    "offer_service": "offer_id,service_id", # Composite key cho Upsert Supabase
    "offer_coupon": "offer_id,coupon_id",   # Composite key cho Upsert Supabase
    "review": "review_id",
}

def get_postgres_connection():
    return psycopg2.connect(
        user=USER,
        database=DBNAME,
        password=PASSWORD,
        host=HOST,
        port=PORT,
    )

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be configured in the .env file"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)