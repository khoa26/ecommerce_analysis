from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import pandas as pd
import plotly.io as pio
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
import io
import contextlib

root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

web_app_dir = str(Path(__file__).resolve().parents[1] / "web_app")
if web_app_dir not in sys.path:
    sys.path.insert(0, web_app_dir)

from src.web_app.data_engine import build_product_mart

router = APIRouter(prefix="/execute", tags=["Local Execution"])

class ExecuteRequest(BaseModel):
    code: str

def call_log_api(entry: dict):
    """Hàm thực hiện HTTP POST gọi sang API Logs"""
    try:
        requests.post("http://127.0.0.1:8000/logs/save", json=entry, timeout=3)
    except Exception as e:
        print(f"[Warning] Không thể gọi API Logs: {e}")

@router.post("")
async def run_code(request: ExecuteRequest, background_tasks: BackgroundTasks):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "EXECUTE",
        "executed_code": request.code,
        "status": "pending",
        "result_type": None,
        "analysis_output": None,
        "execution_logs": None,
        "error_detail": None
    }
    
    stdout_capture = io.StringIO()
    
    try:
        df = build_product_mart()
        local_namespace = {}
        
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stdout_capture):
            exec(request.code, globals(), local_namespace)
            
            if 'analyze' not in local_namespace:
                raise ValueError("Không tìm thấy hàm analyze(df)")
                
            result = local_namespace['analyze'](df)
            
        captured_logs = stdout_capture.getvalue()
        
        if result['type'] == 'dataframe':
            data_sample = result['data'].head(10).to_dict(orient='records')
            log_entry.update({
                "status": "success",
                "result_type": "dataframe",
                "analysis_output": data_sample,
                "execution_logs": captured_logs
            })
            # Đẩy việc gọi API ghi log vào chạy ngầm
            background_tasks.add_task(call_log_api, log_entry)
            
            return {
                "status": "success", 
                "type": "dataframe", 
                "data": result['data'].head(100).to_dict(orient='records'),
                "logs": captured_logs
            }
            
        elif result['type'] == 'plotly_json':
            fig_json = pio.to_json(result['data'])
            log_entry.update({
                "status": "success",
                "result_type": "plotly_json",
                "analysis_output": json.loads(fig_json),
                "execution_logs": captured_logs
            })
            # Đẩy việc gọi API ghi log vào chạy ngầm
            background_tasks.add_task(call_log_api, log_entry)
            
            return {
                "status": "success", 
                "type": "plotly_json", 
                "data": fig_json,
                "logs": captured_logs
            }

    except Exception as e:
        captured_logs = stdout_capture.getvalue()
        log_entry.update({
            "status": "failed",
            "execution_logs": captured_logs,
            "error_detail": str(e)
        })
        background_tasks.add_task(call_log_api, log_entry)
        raise HTTPException(status_code=400, detail=f"Lỗi: {str(e)}\nLogs: {captured_logs}")