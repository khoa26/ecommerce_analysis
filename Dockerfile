FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (many Python wheels are available, but keep build tools for safety)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install ONLY packages needed by `src/api/` + `src/ai_module/`
# (do not rely on the project's full requirements.txt)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    requests \
    python-dotenv \
    google-genai \
    pandas \
    numpy \
    plotly \
    pyarrow \
    streamlit

# Copy only what the API needs at runtime
COPY src ./src
COPY data ./data

EXPOSE 8000

# Use --app-dir so `main.py` can import `ai_service`, `executor`, `logger`
CMD ["uvicorn", "main:app", "--app-dir", "src/api", "--host", "0.0.0.0", "--port", "8000"]
