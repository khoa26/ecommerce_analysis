from __future__ import annotations

import contextlib
import io
import json
import multiprocessing as mp
import re
import sys
import traceback
from typing import Any

from pathlib import Path

_ROOT_DIR = str(Path(__file__).resolve().parents[2])
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)


_FORBIDDEN_PATTERNS = [
    r"\bimport\s+os\b",
    r"\bimport\s+sys\b",
    r"\bimport\s+subprocess\b",
    r"\bimport\s+socket\b",
    r"\bimport\s+pathlib\b",
    r"\bfrom\s+os\b",
    r"\bfrom\s+sys\b",
    r"\bfrom\s+subprocess\b",
    r"\bfrom\s+socket\b",
    r"__\w+__",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bopen\s*\(",
]

_ALLOWED_IMPORT_ROOTS = {
    "pandas",
    "numpy",
    "plotly",
    "math",
    "statistics",
}


def _safe_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
    root = (name or "").split(".")[0]
    if root not in _ALLOWED_IMPORT_ROOTS:
        raise ImportError(f"Import '{name}' không được phép")
    return __import__(name, globals, locals, fromlist, level)


def _validate_code(code: str) -> None:
    if not code or not code.strip():
        raise ValueError("Code rỗng.")
    if len(code) > 20_000:
        raise ValueError("Code quá dài (tối đa 20,000 ký tự).")
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, code):
            raise ValueError("Code chứa hành vi/keyword không được phép.")
    if "def analyze" not in code:
        raise ValueError("Không tìm thấy hàm analyze(df).")


def _worker(code: str, max_rows: int, queue: mp.Queue) -> None:
    stdout_capture = io.StringIO()
    try:
        _validate_code(code)

        # Import inside worker to keep parent lightweight
        import pandas as pd  # noqa: F401
        import plotly.io as pio
        from src.web_app.data_engine import build_mart, get_processed_signature

        df = build_mart(get_processed_signature())

        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "__import__": _safe_import,
        }

        g: dict[str, Any] = {"__builtins__": safe_builtins}
        l: dict[str, Any] = {}

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stdout_capture):
            exec(code, g, l)

            analyze = l.get("analyze") or g.get("analyze")
            if not callable(analyze):
                raise ValueError("Không tìm thấy hàm analyze(df) sau khi thực thi code.")

            result = analyze(df)

        logs = stdout_capture.getvalue()
        if not isinstance(result, dict) or "type" not in result:
            raise ValueError("Hàm analyze(df) phải return dict có khóa 'type'.")

        rtype = result.get("type")
        payload: dict[str, Any] = {"status": "success", "type": rtype, "logs": logs}

        if rtype == "dataframe":
            data = result.get("data")
            if not hasattr(data, "to_dict"):
                raise ValueError("Kết quả dataframe không hợp lệ.")
            payload["data"] = data.head(max_rows).to_dict(orient="records")
        elif rtype == "plotly_json":
            data = result.get("data")
            if isinstance(data, str):
                payload["data"] = data
            else:
                payload["data"] = pio.to_json(data)
        else:
            raise ValueError("type chỉ được phép: 'dataframe' hoặc 'plotly_json'.")

        queue.put(payload)
    except Exception as e:
        logs = stdout_capture.getvalue()
        queue.put(
            {
                "status": "failed",
                "error": str(e),
                "logs": logs,
                "traceback": traceback.format_exc(limit=5),
            }
        )


def run_analysis_code(code: str, timeout_s: int = 10, max_rows: int = 100) -> dict[str, Any]:
    """
    Thực thi code AI sinh ra trong process riêng, có timeout.
    Trả về payload JSON-safe cho API.
    """
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_worker, args=(code, max_rows, queue), daemon=True)
    proc.start()
    proc.join(timeout=timeout_s)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        return {
            "status": "failed",
            "error": f"Timeout: quá {timeout_s}s.",
            "logs": "",
        }

    if queue.empty():
        return {"status": "failed", "error": "Không nhận được kết quả thực thi.", "logs": ""}

    out = queue.get()
    # Ensure JSON serializable (defensive)
    json.dumps(out, ensure_ascii=False)
    return out

