FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# System deps (pyarrow/pandas wheels generally available; keep build tools for safety)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Frontend dependencies (Streamlit app)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pyarrow

# Copy Streamlit frontend + data
COPY src/web_app ./src/web_app
COPY data ./data

EXPOSE 8501

# Use platform-injected $PORT when available (Railway/Render/etc.)
CMD ["sh", "-c", "streamlit run src/web_app/app.py --server.headless true --server.address 0.0.0.0 --server.port ${PORT:-8501}"]