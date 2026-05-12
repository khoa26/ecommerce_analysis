from __future__ import annotations

import json
import time
import uuid
import streamlit as st
import pandas as pd
import plotly.io as pio
import requests
from dataclasses import dataclass
from typing import Any, Literal, Optional

from config import *
import os

from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv("API_URL")
MAX_EVENTS = 30
KEEP_FULL_DATA_EVENTS = 8
REQUEST_TIMEOUT_S = (5, 60)  # (connect, read)
EXECUTOR_TIMEOUT_S = (5, 120)
MAX_DF_ROWS_STORED = 500

@dataclass
class ChatEvent:
    id: str
    role: Literal["user", "assistant"]
    type: Literal["text", "pending_code", "result_df", "result_plotly", "error"]
    content: str
    code: Optional[str] = None
    data: Optional[Any] = None
    is_executed: bool = False  # Đánh dấu xem đoạn code này đã được người dùng duyệt/chạy chưa
    parent_id: Optional[str] = None  # Liên kết phản hồi với message gốc (user/pending_code)
    created_at: float = 0.0


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> float:
    return time.time()


def _require_api_url() -> str:
    if not API_URL:
        raise RuntimeError("Thiếu cấu hình `API_URL` (env). Vui lòng đặt `API_URL` trỏ tới FastAPI backend.")
    return API_URL


@st.cache_resource
def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _trim_chat_events() -> None:
    """Bound memory by trimming history and dropping heavy artifacts for older events."""
    events: list[ChatEvent] = st.session_state.get("chat_events", [])
    if not events:
        return

    # Keep only most recent MAX_EVENTS
    events = events[-MAX_EVENTS:]

    # Drop heavy `data` for older events (keep latest KEEP_FULL_DATA_EVENTS intact)
    if len(events) > KEEP_FULL_DATA_EVENTS:
        for ev in events[:-KEEP_FULL_DATA_EVENTS]:
            if ev.type in ("result_df", "result_plotly"):
                ev.data = None

    st.session_state.chat_events = events


def _has_child_event(parent_id: str, child_types: tuple[str, ...]) -> bool:
    for ev in st.session_state.get("chat_events", []):
        if ev.parent_id == parent_id and ev.type in child_types:
            return True
    return False

def call_ai_generate(query: str) -> dict:
    """Gọi API sinh code của AI"""
    base = _require_api_url()
    response = _http_session().post(
        f"{base}/ai/generate",
        json={"query": query},
        timeout=REQUEST_TIMEOUT_S,
    )

    if response.status_code != 200:
        try:
            error_detail = response.json().get("detail", response.text)
        except Exception:
            error_detail = response.text
        raise Exception(f"Chi tiết lỗi từ Backend: {error_detail}")
        
    return response.json()

def call_executor(code: str) -> dict:
    """Gửi code đã duyệt xuống API Thực thi Local"""
    base = _require_api_url()
    response = _http_session().post(
        f"{base}/execute",
        json={"code": code},
        timeout=EXECUTOR_TIMEOUT_S,
    )
    
    if response.status_code != 200:
        # Giúp debug lỗi tốt hơn
        try:
            error_detail = response.json().get("detail", "Lỗi thực thi không xác định")
        except:
            error_detail = response.text
        raise Exception(error_detail)
    return response.json()

def _ensure_chat_state() -> None:
    st.session_state.setdefault("processing_generate", False)
    st.session_state.setdefault("generate_inflight_for", None)  # user_event_id
    st.session_state.setdefault("generate_inflight_started_at", 0.0)
    st.session_state.setdefault("execute_request", None)  # {"event_id": str, "code": str}
    st.session_state.setdefault("reject_request", None)  # event_id
    st.session_state.setdefault("chat_events", [])

    # Migrate legacy ChatEvent objects that may exist across hot-reload/redeploy.
    events = st.session_state.get("chat_events") or []
    changed = False
    for idx, ev in enumerate(events):
        # Some older sessions may have dicts or older dataclass instances without new fields.
        if isinstance(ev, dict):
            # Best-effort conversion
            role = ev.get("role", "assistant")
            ev_type = ev.get("type", "text")
            content = ev.get("content", "")
            code = ev.get("code")
            data = ev.get("data")
            is_executed = bool(ev.get("is_executed", False))
            parent_id = ev.get("parent_id")
            created_at = float(ev.get("created_at") or 0.0)
            new_ev = ChatEvent(
                id=ev.get("id") or _new_id("legacy"),
                role=role,
                type=ev_type,
                content=content,
                code=code,
                data=data,
                is_executed=is_executed,
                parent_id=parent_id,
                created_at=created_at,
            )
            events[idx] = new_ev
            changed = True
            continue

        if not hasattr(ev, "id") or not getattr(ev, "id"):
            setattr(ev, "id", _new_id("legacy"))
            changed = True
        if not hasattr(ev, "parent_id"):
            setattr(ev, "parent_id", None)
            changed = True
        if not hasattr(ev, "created_at"):
            setattr(ev, "created_at", 0.0)
            changed = True

    if changed:
        st.session_state.chat_events = events


def _coerce_df_payload(data: Any) -> Any:
    """Limit stored DF payload to avoid session memory blowups."""
    try:
        if isinstance(data, list) and len(data) > MAX_DF_ROWS_STORED:
            return data[:MAX_DF_ROWS_STORED]
    except Exception:
        pass
    return data


def _process_execute_request() -> None:
    req = st.session_state.get("execute_request")
    if not req:
        return

    event_id = req.get("event_id")
    code = req.get("code")
    st.session_state.execute_request = None

    if not event_id or not isinstance(code, str):
        return

    # Find the pending_code event by id
    events: list[ChatEvent] = st.session_state.get("chat_events", [])
    idx = next((i for i, ev in enumerate(events) if ev.id == event_id), None)
    if idx is None:
        return

    pending_ev = events[idx]
    if pending_ev.type != "pending_code":
        return

    # Idempotency: if already executed, do nothing
    if pending_ev.is_executed:
        return

    pending_ev.is_executed = True
    pending_ev.code = code

    with st.chat_message("assistant"):
        with st.spinner("Đang thực thi mã..."):
            try:
                res = call_executor(code)
                if res.get("status") != "success":
                    raise Exception(res.get("detail") or "Lỗi thực thi không xác định")

                if res.get("type") == "dataframe":
                    payload = _coerce_df_payload(res.get("data"))
                    note = ""
                    if isinstance(res.get("data"), list) and isinstance(payload, list) and len(payload) < len(res["data"]):
                        note = f"\n\n_(Đã giới hạn hiển thị {MAX_DF_ROWS_STORED} dòng để tiết kiệm bộ nhớ)_"
                    st.session_state.chat_events.append(
                        ChatEvent(
                            id=_new_id("a"),
                            role="assistant",
                            type="result_df",
                            content="📊 **Kết quả dữ liệu:**" + note,
                            data=payload,
                            is_executed=True,
                            parent_id=pending_ev.id,
                            created_at=_now(),
                        )
                    )
                elif res.get("type") == "plotly_json":
                    st.session_state.chat_events.append(
                        ChatEvent(
                            id=_new_id("a"),
                            role="assistant",
                            type="result_plotly",
                            content="📈 **Biểu đồ phân tích:**",
                            data=res.get("data"),
                            is_executed=True,
                            parent_id=pending_ev.id,
                            created_at=_now(),
                        )
                    )
                else:
                    st.session_state.chat_events.append(
                        ChatEvent(
                            id=_new_id("a"),
                            role="assistant",
                            type="text",
                            content="Đã thực thi xong, nhưng backend không trả về kiểu kết quả hỗ trợ hiển thị.",
                            is_executed=True,
                            parent_id=pending_ev.id,
                            created_at=_now(),
                        )
                    )

            except Exception as e:
                st.session_state.chat_events.append(
                    ChatEvent(
                        id=_new_id("a"),
                        role="assistant",
                        type="error",
                        content=f"❌ **Lỗi thực thi:**\n{str(e)}",
                        is_executed=True,
                        parent_id=pending_ev.id,
                        created_at=_now(),
                    )
                )

    _trim_chat_events()


def _process_reject_request() -> None:
    event_id = st.session_state.get("reject_request")
    if not event_id:
        return

    st.session_state.reject_request = None
    events: list[ChatEvent] = st.session_state.get("chat_events", [])
    idx = next((i for i, ev in enumerate(events) if ev.id == event_id), None)
    if idx is None:
        return

    ev = events[idx]
    if ev.type != "pending_code" or ev.is_executed:
        return

    ev.is_executed = True
    st.session_state.chat_events.append(
        ChatEvent(
            id=_new_id("a"),
            role="assistant",
            type="text",
            content="Đã hủy bỏ việc thực thi đoạn mã trên.",
            is_executed=True,
            parent_id=ev.id,
            created_at=_now(),
        )
    )
    _trim_chat_events()


def _process_generate_if_needed() -> None:
    """Generate code for the most recent unprocessed user message (idempotent)."""
    events: list[ChatEvent] = st.session_state.get("chat_events", [])
    if not events:
        return

    # Find newest user message without an assistant response (pending_code or error) linked to it.
    target_user: Optional[ChatEvent] = None
    for ev in reversed(events):
        if ev.role != "user" or ev.type != "text":
            continue
        if _has_child_event(ev.id, ("pending_code", "error")):
            continue
        target_user = ev
        break

    if not target_user:
        return

    inflight_for = st.session_state.get("generate_inflight_for")
    inflight_started = float(st.session_state.get("generate_inflight_started_at") or 0.0)

    # If a previous run was interrupted mid-request, don't instantly duplicate-call.
    if inflight_for == target_user.id and (_now() - inflight_started) < 90:
        return

    st.session_state.generate_inflight_for = target_user.id
    st.session_state.generate_inflight_started_at = _now()

    with st.chat_message("assistant"):
        with st.spinner("AI đang phân tích dữ liệu và sinh mã nguồn..."):
            try:
                ai_response = call_ai_generate(target_user.content)
                st.session_state.chat_events.append(
                    ChatEvent(
                        id=_new_id("a"),
                        role="assistant",
                        type="pending_code",
                        content=ai_response.get("explanation", ""),
                        code=ai_response.get("code", ""),
                        is_executed=False,
                        parent_id=target_user.id,
                        created_at=_now(),
                    )
                )
            except Exception as e:
                st.session_state.chat_events.append(
                    ChatEvent(
                        id=_new_id("a"),
                        role="assistant",
                        type="error",
                        content=str(e),
                        is_executed=True,
                        parent_id=target_user.id,
                        created_at=_now(),
                    )
                )
            finally:
                st.session_state.generate_inflight_for = None
                st.session_state.generate_inflight_started_at = 0.0

    _trim_chat_events()

def chatbot_area(mart_filtered: pd.DataFrame) -> None:
    st.markdown("### 🤖 Trợ lý AI Phân tích")
    # st.caption("Nhập yêu cầu bằng ngôn ngữ tự nhiên. AI sẽ sinh mã Python và chờ bạn duyệt/chỉnh sửa trước khi thực thi.")

    _ensure_chat_state()

    # Input (adds a user message once; generation is idempotent by message id)
    prompt = st.chat_input("Ví dụ: Vẽ biểu đồ top 5 ngành hàng có doanh thu ước tính cao nhất")
    if prompt:
        st.session_state.chat_events.append(
            ChatEvent(
                id=_new_id("u"),
                role="user",
                type="text",
                content=prompt,
                is_executed=True,
                parent_id=None,
                created_at=_now(),
            )
        )
        _trim_chat_events()

    # Process side-effects (safe on rerun due to idempotent guards)
    _process_reject_request()
    _process_execute_request()
    _process_generate_if_needed()

    # Hiển thị lịch sử chat
    for i, ev in enumerate(st.session_state.chat_events):
        with st.chat_message(ev.role):
            if ev.type == "text":
                st.markdown(ev.content)
            
            elif ev.type == "pending_code":
                st.markdown(f"**💡 Giải thích:** {ev.content}")
                
                if not ev.is_executed:
                    st.info("Trạng thái: Đang chờ duyệt. Bạn có thể chỉnh sửa mã nguồn bên dưới trước khi chạy.")
                    # Cho phép chỉnh sửa code
                    edited_code = st.text_area("Mã nguồn (Python):", value=ev.code or "", height=250, key=f"code_{ev.id}")
                    
                    col1, col2 = st.columns([1.5, 5])
                    with col1:
                        if st.button("🚀 Duyệt & Chạy", key=f"btn_{ev.id}", type="primary"):
                            st.session_state.execute_request = {"event_id": ev.id, "code": edited_code}
                    with col2:
                        if st.button("❌ Hủy bỏ", key=f"reject_{ev.id}"):
                            st.session_state.reject_request = ev.id
                else:
                    st.markdown("**Đoạn mã đã chốt & thực thi:**")
                    st.code(ev.code, language="python")

            elif ev.type == "result_df":
                st.markdown(ev.content)
                if ev.data is None:
                    st.caption("Kết quả cũ đã được giải phóng để tiết kiệm bộ nhớ phiên.")
                else:
                    st.dataframe(pd.DataFrame(ev.data))
            
            elif ev.type == "result_plotly":
                st.markdown(ev.content)
                if ev.data is None:
                    st.caption("Biểu đồ cũ đã được giải phóng để tiết kiệm bộ nhớ phiên.")
                else:
                    fig = pio.from_json(ev.data)
                    st.plotly_chart(fig, use_container_width=True)
            
            elif ev.type == "error":
                st.error(ev.content)

def load_chat_history() -> list[ChatEvent]:
    """Gọi API Logs, xử lý dữ liệu và tái tạo lại 2 phiên chat gần nhất"""
    try:
        base = _require_api_url()
        response = _http_session().get(f"{base}/logs/history?limit=15", timeout=(3, 10))
        if response.status_code == 200:
            history_data = response.json().get("data", [])
            new_events = []
            
            # Duyệt từ cũ đến mới
            for entry in reversed(history_data):
                # 1. Tái tạo câu hỏi và đoạn code của AI
                if entry.get("action") == "CHAT_SESSION":
                    user_q, ai_exp, ai_code = "", "", ""
                    for ev in entry.get("events", []):
                        if ev.get("role") == "user":
                            user_q = ev.get("content")
                        elif ev.get("type") == "text":
                            ai_exp = ev.get("content")
                        elif ev.get("type") == "code":
                            ai_code = ev.get("content")
                            
                    # Thêm câu hỏi User
                    if user_q:
                        user_id = _new_id("u_hist")
                        new_events.append(
                            ChatEvent(
                                id=user_id,
                                role="user",
                                type="text",
                                content=user_q,
                                is_executed=True,
                                parent_id=None,
                                created_at=_now(),
                            )
                        )
                    # Thêm Code AI (đánh dấu is_executed=True để web hiện dạng đã chốt)
                    if ai_exp or ai_code:
                        # link to the immediately previous user event if present
                        parent_id = new_events[-1].id if new_events and new_events[-1].role == "user" else None
                        new_events.append(
                            ChatEvent(
                                id=_new_id("a_hist"),
                                role="assistant",
                                type="pending_code",
                                content=ai_exp,
                                code=ai_code,
                                is_executed=True,
                                parent_id=parent_id,
                                created_at=_now(),
                            )
                        )
                        
                # 2. Tái tạo Kết quả biểu đồ/bảng dữ liệu
                elif entry.get("action") == "EXECUTE" and entry.get("status") == "success":
                    ev_type = entry.get("type", "result_df")
                    data_to_pass = entry.get("analysis_output")
                    
                    # QUAN TRỌNG: Xử lý bẫy lỗi Plotly (Ép kiểu dict về string)
                    if ev_type == "result_plotly" and isinstance(data_to_pass, dict):
                        data_to_pass = json.dumps(data_to_pass)

                    new_events.append(ChatEvent(
                        id=_new_id("a_hist"),
                        role=entry.get("role", "assistant"),
                        type=ev_type,
                        content=entry.get("content", "📊 Kết quả lịch sử:"),
                        data=data_to_pass,
                        is_executed=True
                    ))
            
            # Trả về 8 sự kiện cuối cùng (tương đương 2 lần hỏi đáp + biểu đồ)
            return new_events[-8:]
    except Exception as e:
        print(f"Lỗi load lịch sử: {e}")
        return []
    return []