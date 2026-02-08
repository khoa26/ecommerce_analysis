import os
import time
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from supabase import create_client, Client

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("PASSWORD")
DB_HOST = os.getenv("HOST")
DB_DATABASE = os.getenv("DATABASE")
DB_PORT = os.getenv("PORT")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BATCH_SIZE = int(os.getenv("UPLOAD_BATCH_SIZE", "1000"))

TABLE_ORDER = [
    "category",   # category_id, category_name, category_url, parent_category_id, level, category_path, is_scanned
    "seller",     # seller_id, seller_name, seller_rating, total_reviews
    "reviewer",   # reviewer_id, reviewer_name, reviewer_seniority, reviewer_contributions, reviewer_received_thanks
    "product",    # product_id, product_name, short_description, category_id, seller_id, product_url, image_url, author_brand, sold_quantity, review_score, review_count
    "price_offer",# offer_id, product_id, current_price, original_price, discount_percent, coupon_available, extra_services, crawl_time
    "review",     # review_id, product_id, reviewer_id, rating_score, review_content, thank_count, review_time, usage_duration
]

PRIMARY_KEYS = {
    "category": "category_id",
    "seller": "seller_id",
    "reviewer": "reviewer_id",
    "product": "product_id",
    "price_offer": "offer_id",
    "review": "review_id",
}

def get_postgres_connection():
    return psycopg2.connect(
        user=DB_USER,
        database=DB_DATABASE,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be configured in the .env file"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def read_table_from_postgres(conn, table_name: str) -> pd.DataFrame:
    if table_name == "category":
        query = "SELECT * FROM category ORDER BY level ASC NULLS FIRST"
    else:
        query = f'SELECT * FROM "{table_name}"'
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.read_sql_query(query, conn)


def _to_json_serializable(value: Any) -> Any:
    """Convert pandas Timestamp / datetime to ISO string for JSON."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def convert_dataframe_to_dict(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = df.where(pd.notnull(df), None)
    rows = df.to_dict("records")
    return [
        {k: _to_json_serializable(v) for k, v in row.items()}
        for row in rows
    ]


def _clear_supabase_table(supabase: Client, table_name: str) -> None:
    pk = PRIMARY_KEYS.get(table_name)
    if not pk:
        print(f"    Warning: unknown table '{table_name}', skip clear")
        return
    print(f"  Clearing existing data from '{table_name}'...")
    try:
        supabase.table(table_name).delete().neq(pk, "").execute()
    except Exception as e:
        print(f"    Warning: could not clear table: {e}")


def upload_table_batch(
    supabase: Client,
    table_name: str,
    data: List[Dict[str, Any]],
    batch_size: int = BATCH_SIZE
) -> tuple[int, int]:

    total_records = len(data)
    success_count = 0
    error_count = 0
    pk_column = PRIMARY_KEYS.get(table_name, "id")
    print(f"  Uploading {total_records} records to '{table_name}'...")
    
    for i in range(0, total_records, batch_size):
        batch = data[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        try:
            response = supabase.table(table_name).upsert(
                batch,
                on_conflict=pk_column
            ).execute()
            
            success_count += len(batch)
            print(
                f"    Batch {batch_num}/{total_batches}: "
                f"{len(batch)} records uploaded successfully"
            )
            
        except Exception as e:
            error_count += len(batch)
            print(f"    Batch {batch_num}/{total_batches}: Error - {str(e)}")
            for record in batch:
                try:
                    supabase.table(table_name).upsert(
                        [record],
                        on_conflict=pk_column
                    ).execute()
                    success_count += 1
                    error_count -= 1
                except Exception as record_error:
                    rid = record.get(pk_column, record.get('id', 'unknown'))
                    print(f"      Failed record: {rid} - {str(record_error)}")
        
        if i + batch_size < total_records:
            time.sleep(0.1)
    
    return success_count, error_count


def upload_table(
    supabase: Client,
    table_name: str,
    data: List[Dict[str, Any]],
    clear_existing: bool = False
) -> bool:
    if not data:
        print(f"  Table '{table_name}' is empty, skipping...")
        return True
    
    try:
        success_count, error_count = upload_table_batch(supabase, table_name, data)
        
        print(
            f"  ✓ '{table_name}': {success_count} success, "
            f"{error_count} errors out of {len(data)} total"
        )
        
        return error_count == 0
        
    except Exception as e:
        print(f"  ✗ Error uploading '{table_name}': {str(e)}")
        return False


def upload_all_tables(
    clear_existing: bool = False,
    tables_order: List[str] = None,
) -> Dict[str, bool]:
    if tables_order is None:
        tables_order = TABLE_ORDER

    results = {}

    print("=" * 70)
    print("Starting data migration from PostgreSQL to Supabase")
    print("=" * 70)

    print("\n1. Connecting to databases...")
    try:
        pg_conn = get_postgres_connection()
        print("  ✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"  ✗ Failed to connect to PostgreSQL: {e}")
        return results
    
    try:
        supabase = get_supabase_client()
        print("  ✓ Connected to Supabase")
    except Exception as e:
        print(f"  ✗ Failed to connect to Supabase: {e}")
        pg_conn.close()
        return results

    if clear_existing:
        print("\n2. Clearing existing Supabase data (reverse FK order)...")
        for table_name in reversed(tables_order):
            _clear_supabase_table(supabase, table_name)

    print(f"\n3. Uploading {len(tables_order)} tables...")
    for table_name in tables_order:
        print(f"\nProcessing table: {table_name}")
        
        try:
            df = read_table_from_postgres(pg_conn, table_name)
            print(f"  Found {len(df)} records in PostgreSQL")
            
            if len(df) == 0:
                print(f"  Skipping empty table '{table_name}'")
                results[table_name] = True
                continue
            
            data = convert_dataframe_to_dict(df)
            
            success = upload_table(supabase, table_name, data)
            
            results[table_name] = success
            
        except Exception as e:
            print(f"  ✗ Error processing '{table_name}': {str(e)}")
            results[table_name] = False
    
    pg_conn.close()
    
    print("\n" + "=" * 70)
    print("Upload Summary")
    print("=" * 70)
    
    for table_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {table_name}: {status}")
    
    total_success = sum(1 for s in results.values() if s)
    print(f"\nTotal: {total_success}/{len(results)} tables uploaded successfully")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Upload data from PostgreSQL to Supabase'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing data in Supabase before uploading'
    )
    parser.add_argument(
        '--tables',
        nargs='+',
        help='Specific tables to upload (default: all tables)',
        default=None
    )
    
    args = parser.parse_args()
    
    upload_all_tables(
        clear_existing=args.clear,
        tables_order=args.tables
    )


if __name__ == "__main__":
    main()
