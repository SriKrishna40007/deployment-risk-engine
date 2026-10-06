FROM python:3.13-slim

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY app.py .

USER 10001

EXPOSE 8080

CMD ["python", "app.py"]
