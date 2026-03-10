import os
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from psycopg2.extras import execute_values
from _shared import get_postgres_connection, PRIMARY_KEYS, TABLE_ORDER

CSV_DIR = Path(__file__).resolve().parent / "team_csv_data"

SMART_TABLES = {
    "service": {"name_col": "service_name", "id_col": "service_id"},
    "coupon": {"name_col": "coupon_code", "id_col": "coupon_id"}
}

JUNCTION_TABLES = {
    "offer_service": {"ref_table": "service", "ref_col": "service_id"},
    "offer_coupon": {"ref_table": "coupon", "ref_col": "coupon_id"}
}

ID_MAPPINGS = {}

def get_valid_db_columns(conn, table_name):
    """Lấy danh sách các cột thực sự tồn tại trong PostgreSQL để lọc rác từ CSV"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
            (table_name,)
        )
        return [row[0] for row in cur.fetchall()]

def get_local_mapping(conn, table_name, name_col, id_col):
    with conn.cursor() as cur:
        cur.execute(f'SELECT "{name_col}", "{id_col}" FROM "{table_name}"')
        return dict(cur.fetchall())

def upsert_df_to_db(conn, table_name, df, conflict_cols):
    columns = list(df.columns)
    real_pk_cols = PRIMARY_KEYS.get(table_name, "id").split(",")
    
    update_cols = [col for col in columns if col not in conflict_cols and col not in real_pk_cols]
    
    if update_cols:
        set_clause = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])
        conflict_action = f"DO UPDATE SET {set_clause}"
    else:
        conflict_action = "DO NOTHING"

    cols_string = ", ".join([f'"{col}"' for col in columns])
    pks_string = ", ".join([f'"{pk}"' for pk in conflict_cols])
    
    query = f"""
        INSERT INTO "{table_name}" ({cols_string})
        VALUES %s
        ON CONFLICT ({pks_string}) {conflict_action};
    """
    
    values = [tuple(row) for row in df.values]
    with conn.cursor() as cur:
        execute_values(cur, cur.mogrify(query).decode('utf-8'), values, page_size=2000)
    conn.commit()

def main():
    parser = argparse.ArgumentParser(description='Import dữ liệu CSV vào Database.')
    parser.add_argument('--tables', nargs='+', help='Danh sách các bảng cần load', default=None)
    args = parser.parse_args()

    if not CSV_DIR.exists():
        print(f"Thư mục {CSV_DIR} không tồn tại.")
        return

    print("=" * 60)
    print("BẮT ĐẦU HỢP NHẤT DỮ LIỆU CSV VÀO LOCAL DATABASE")
    print("=" * 60)

    try:
        conn = get_postgres_connection()
    except Exception as e:
        print(f"Không thể kết nối Database: {e}")
        return

    tables_to_run = TABLE_ORDER
    if args.tables:
        tables_to_run = [t for t in TABLE_ORDER if t in args.tables]

    for table_name in tables_to_run:
        csv_path = CSV_DIR / f"{table_name}.csv"
        if not csv_path.exists():
            continue

        print(f"\nĐang xử lý: {table_name}...")
        try:
            # Dùng low_memory=False để tránh cảnh báo DtypeWarning cho các file lớn
            df = pd.read_csv(csv_path, low_memory=False)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            if df.empty:
                continue

            # --- CƠ CHẾ TỰ VỆ 1: CHUẨN HÓA DỮ LIỆU RÁC (Trị lỗi category) ---
            df = df.replace({'NaN': None, 'nan': None, '<NA>': None, np.nan: None})
            df = df.where(pd.notnull(df), None)

            # --- CƠ CHẾ TỰ VỆ 2: LỌC CỘT RÁC TỪ CSV (Trị lỗi price_offer) ---
            valid_db_cols = get_valid_db_columns(conn, table_name)
            drop_cols = [c for c in df.columns if c not in valid_db_cols]
            if drop_cols:
                print(f"  -> Tự động cắt bỏ các cột dư thừa không có trong DB: {drop_cols}")
                df = df.drop(columns=drop_cols)

            if table_name in JUNCTION_TABLES:
                ref_table = JUNCTION_TABLES[table_name]["ref_table"]
                ref_col = JUNCTION_TABLES[table_name]["ref_col"]
                if ref_table in ID_MAPPINGS:
                    df[ref_col] = df[ref_col].map(ID_MAPPINGS[ref_table]).fillna(df[ref_col])
                    print(f"  -> Đã dịch ID theo chuẩn Local cho cột {ref_col}.")

            original_df = None
            if table_name in SMART_TABLES:
                name_col = SMART_TABLES[table_name]["name_col"]
                id_col = SMART_TABLES[table_name]["id_col"]
                conflict_cols = [name_col]
                original_df = df.copy() 
                if id_col in df.columns:
                    df = df.drop(columns=[id_col])
            # --- CƠ CHẾ TỰ VỆ 3: UNIQUE CONSTRAINT (Trị lỗi review) ---
            elif table_name == "review":
                conflict_cols = ["product_id", "reviewer_id"]
            else:
                pk_string = PRIMARY_KEYS.get(table_name, "id")
                conflict_cols = pk_string.split(",")

            if set(conflict_cols).issubset(df.columns):
                df = df.drop_duplicates(subset=conflict_cols, keep='first')

            upsert_df_to_db(conn, table_name, df, conflict_cols)
            print(f"  ✓ Hợp nhất thành công {len(df)} dòng.")

            if table_name in SMART_TABLES and original_df is not None:
                name_col = SMART_TABLES[table_name]["name_col"]
                id_col = SMART_TABLES[table_name]["id_col"]
                local_mapping = get_local_mapping(conn, table_name, name_col, id_col)
                mapping_dict = {}
                for _, row in original_df.dropna(subset=[id_col, name_col]).iterrows():
                    old_id = row[id_col]
                    name = row[name_col]
                    if name in local_mapping:
                        mapping_dict[old_id] = local_mapping[name]
                ID_MAPPINGS[table_name] = mapping_dict
                print(f"  -> Đã tạo bộ từ điển {len(mapping_dict)} ID cho bảng {table_name}.")

        except Exception as e:
            conn.rollback()
            print(f"  ✗ Lỗi khi xử lý {table_name}: {e}")

    conn.close()
    print("\n" + "=" * 60)
    print("HOÀN TẤT HỢP NHẤT DỮ LIỆU!")

if __name__ == "__main__":
    main()