FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN groupadd --gid 50000 app && useradd --uid 50000 --gid 50000 --create-home app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R app:app /app
USER app
EXPOSE 8001

CMD ["gunicorn", "ticket_service.config.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]
