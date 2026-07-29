FROM python:3.11-slim

WORKDIR /app

# Install deps first so this layer is cached across rebuilds when only app.py changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 7860

# GEMINI_API_KEY is intentionally NOT set here — the user supplies their own at `docker run`
CMD ["python", "app.py"]
