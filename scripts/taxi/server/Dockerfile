# EV7 Smart Taxi Monitor — web server + AI-agent proxy
# The built web folder contains plates / VINs / positions, so it is NOT baked into the image:
# mount it at run time, e.g.
#   docker build -t ev7-monitor scripts/taxi/server
#   docker run -p 8080:8080 -v D:/Taxi/dashboard_v3:/web:ro \
#     -e ANTHROPIC_API_KEY -e EV7_USER=ops -e EV7_PASS ev7-monitor
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV WEB_DIR=/web
EXPOSE 8080
USER nobody
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
