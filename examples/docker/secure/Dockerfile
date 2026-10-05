FROM python:3.13-slim

RUN useradd --create-home appuser

WORKDIR /app

COPY app.py .

USER appuser

CMD ["python", "app.py"]
