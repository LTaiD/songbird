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
# /tmp caches: HF Spaces run the container as a non-root user, so numba/mpl/keras
# must not write into the read-only image or a non-writable HOME.
ENV KERAS_BACKEND=torch \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/tmp \
    MPLCONFIGDIR=/tmp \
    KERAS_HOME=/tmp/.keras \
    XDG_CACHE_HOME=/tmp/.cache \
    HF_HOME=/tmp/.hf
# hand landmarker model is fetched on first use; bake it in so cold starts are
# fast AND it's readable at runtime (the non-root user can't write /app).
RUN python -c "from backend.app.vision.hands import _ensure_model; _ensure_model()" \
    && chmod -R a+rX /app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
