from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ai_service import router as ai_router
from executor import router as executor_router
from logger import router as logger_router

app = FastAPI(
    title="Tiki Data AI Agent API",
    description="Backend API phục vụ hệ thống Human-in-the-loop phân tích dữ liệu Tiki",
    version="1.0.0"
)

# Cấu hình CORS để Frontend (Streamlit) có thể gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong thực tế có thể giới hạn lại thành ["http://localhost:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nhúng các router vào ứng dụng chính
app.include_router(ai_router)
app.include_router(executor_router)
app.include_router(logger_router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Tiki AI Agent API is running."}

if __name__ == "__main__":
    # Khởi chạy server tại cổng 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)