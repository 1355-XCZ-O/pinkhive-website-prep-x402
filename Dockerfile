FROM python:3.12-slim
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY config config
ENV HOST=0.0.0.0 PORT=8402 METER_DB=/tmp/usage.sqlite3
EXPOSE 8402
CMD ["python", "-m", "app.server"]

