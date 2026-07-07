# Songbird backend — multi-stage (spec Phase 7). Keras 3 on torch; no TF.
FROM python:3.12-slim AS deps
WORKDIR /app
# libgl/libglib: opencv runtime; build tools stay out of the final image
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=deps /install /usr/local
COPY app ./backend/app
ENV KERAS_BACKEND=torch \
    PYTHONUNBUFFERED=1
# hand landmarker model is fetched on first use; bake it in so cold starts are fast
RUN python -c "from backend.app.vision.hands import _ensure_model; _ensure_model()"
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
