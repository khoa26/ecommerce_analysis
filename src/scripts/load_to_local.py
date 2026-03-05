import os
import warnings
from pathlib import Path
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from supabase import create_client, Client
from _shared import get_postgres_connection, PRIMARY_KEYS, TABLE_ORDER, get_supabase_client

def fetch_all_from_supabase(supabase: Client, table_name: str) -> List[Dict[str, Any]]:
    """Tải toàn bộ dữ liệu từ Supabase bằng cách phân trang (Pagination) để tránh giới hạn API."""
    print(f"  Đang tải dữ liệu bảng '{table_name}' từ Supabase...")
    all_data = []
    start = 0
    step = 1000 # Lấy 1000 dòng mỗi lần
    
    while True:
        try:
            response = supabase.table(table_name).select("*").range(start, start + step - 1).execute()
            data = response.data
            
            if not data:
                break
                
            all_data.extend(data)
            
            if len(data) < step:
                break # Đã lấy đến trang cuối cùng
                
            start += step
        except Exception as e:
            print(f"    Lỗi khi tải dữ liệu từ Supabase (bảng {table_name}, offset {start}): {e}")
            break
            
    return all_data

def upsert_to_postgres(conn, table_name: str, data: List[Dict[str, Any]]) -> None:
    """Đẩy dữ liệu vào Local PostgreSQL và xử lý xung đột."""
    if not data:
        print(f"    Bảng '{table_name}' trống trên Supabase, bỏ qua.")
        return

    # Lấy danh sách tên cột từ dictionary đầu tiên
    columns = list(data[0].keys())
    
    # Tách Primary Keys (xử lý cả khóa đa hợp)
    pk_string = PRIMARY_KEYS.get(table_name, "id")
    pk_cols = pk_string.split(",")
    
    # Tạo chuỗi UPDATE SET cho các cột không phải là khóa chính
    update_cols = [col for col in columns if col not in pk_cols]
    
    if update_cols:
        set_clause = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])
        conflict_action = f"DO UPDATE SET {set_clause}"
    else:
        # Nếu bảng chỉ toàn khóa chính (như bảng trung gian offer_coupon), chỉ cần bỏ qua nếu trùng
        conflict_action = "DO NOTHING"

    # Tạo câu lệnh SQL động
    cols_string = ", ".join([f'"{col}"' for col in columns])
    pks_string = ", ".join([f'"{pk}"' for pk in pk_cols])
    
    query = f"""
        INSERT INTO "{table_name}" ({cols_string})
        VALUES %s
        ON CONFLICT ({pks_string}) {conflict_action};
    """
    
    # Chuyển đổi dữ liệu list(dict) sang list(tuple) để execute_values đọc được
    values = [[row.get(col) for col in columns] for row in data]
    
    try:
        with conn.cursor() as cur:
            # execute_values giúp chèn hàng loạt (Bulk Insert) cực nhanh
            execute_values(cur, query, values, page_size=1000)
        conn.commit()
        print(f"  ✓ Đã đồng bộ thành công {len(data)} dòng vào Local DB.")
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Lỗi khi lưu dữ liệu vào Local DB (bảng {table_name}): {e}")

def download_all_tables(tables_order: List[str] = None):
    if tables_order is None:
        tables_order = TABLE_ORDER

    print("=" * 70)
    print("BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU TỪ SUPABASE VỀ LOCAL")
    print("=" * 70)

    try:
        pg_conn = get_postgres_connection()
        print("✓ Đã kết nối Local PostgreSQL")
    except Exception as e:
        print(f"✗ Không thể kết nối Local PostgreSQL: {e}")
        return
    
    try:
        supabase = get_supabase_client()
        print("✓ Đã kết nối Supabase Cloud")
    except Exception as e:
        print(f"✗ Không thể kết nối Supabase: {e}")
        pg_conn.close()
        return

    for table_name in tables_order:
        print(f"\nĐang xử lý bảng: {table_name}")
        # 1. Kéo dữ liệu về
        supabase_data = fetch_all_from_supabase(supabase, table_name)
        
        # 2. Xử lý xung đột và lưu vào Postgres
        if supabase_data:
            upsert_to_postgres(pg_conn, table_name, supabase_data)

    pg_conn.close()
    print("\n" + "=" * 70)
    print("Hoàn tất quá trình đồng bộ!")
    print("=" * 70)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Download data from Supabase to Local PostgreSQL')
    parser.add_argument(
        '--tables',
        nargs='+',
        help='Chỉ định các bảng cần tải về (Mặc định: Toàn bộ bảng)',
        default=None
    )
    
    args = parser.parse_args()
    download_all_tables(tables_order=args.tables)

if __name__ == "__main__":
    main()