# CDN Traffic Analytics

A small FastAPI service for tracking delivery events and summarizing cache efficiency, latency, origin traffic, bandwidth, and estimated egress cost.

The service uses synthetic delivery events and a local SQLite database. It is designed as a portfolio project for learning metrics and traffic analysis, not as a production monitoring system.

## Metrics

- Cache hit ratio
- Average delivery latency
- Total bandwidth
- Origin traffic
- Estimated egress cost
- Region and provider filters

## Run

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8001
```

Open http://127.0.0.1:8001/docs.

Record an event:

```bash
curl -X POST http://127.0.0.1:8001/v1/events \\
  -H 'Content-Type: application/json' \\
  -d '{"region":"us-west","provider":"vendor-a","cache_hit":true,"bytes_sent":1000000,"latency_ms":42,"origin_bytes":0}'
```

Read the summary:

```bash
curl 'http://127.0.0.1:8001/v1/metrics/summary?region=us-west'
```

## Test

```bash
pytest -q
```

## Resume description

> Built a CDN delivery metrics API that aggregates cache-hit ratio, latency, bandwidth, origin traffic, and estimated egress cost by region and provider; added SQLite indexes, REST endpoints, Docker, and automated tests.

