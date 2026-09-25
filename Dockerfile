FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' pydantic
COPY app ./app
RUN mkdir -p /app/data
ENV CDN_ANALYTICS_DB=/app/data/cdn.db
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

