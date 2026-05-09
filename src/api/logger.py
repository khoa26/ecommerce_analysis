from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.scripts._shared import get_postgres_connection

router = APIRouter(prefix="/logs", tags=["System Logging"])

class LogEntry(BaseModel):
    user_query: str
    generated_code: str
    execution_status: str # "success", "error", "rejected"
    error_message: str = None

def save_log_to_db(log: LogEntry):
    """Thao tác ghi log vào PostgreSQL"""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        
        # Tạo bảng nếu chưa tồn tại
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_interaction_logs (
                id SERIAL PRIMARY KEY,
                query TEXT,
                code TEXT,
                status VARCHAR(50),
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            INSERT INTO ai_interaction_logs (query, code, status, error_msg, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (log.user_query, log.generated_code, log.execution_status, log.error_message, datetime.datetime.now()))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Lỗi khi ghi log hệ thống: {e}")

@router.post("/")
async def create_log(log: LogEntry, background_tasks: BackgroundTasks):
    """
    Ghi log bất đồng bộ (Background Task) để không làm chậm API phản hồi cho Frontend.
    """
    background_tasks.add_task(save_log_to_db, log)
    return {"status": "Logged successfully"}