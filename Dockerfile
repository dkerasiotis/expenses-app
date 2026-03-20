FROM python:3.12-slim

WORKDIR /app

# System deps (για pandas + openpyxl κατά την εισαγωγή Excel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY app.py .
COPY init_db.py .
COPY entrypoint.sh .
COPY templates/ templates/
COPY static/ static/

RUN chmod +x entrypoint.sh

# Volume για persistent database
RUN mkdir -p /data

ENV DB_PATH=/data/expenses.db

EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]
