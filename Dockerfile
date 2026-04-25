FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/otp_service/ ./services/otp_service/
COPY shared/ ./shared/

CMD ["uvicorn", "services.otp_service.app:app", "--host", "0.0.0.0", "--port", "8005"]
