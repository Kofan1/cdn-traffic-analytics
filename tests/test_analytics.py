import importlib

def module(tmp_path, monkeypatch):
    monkeypatch.setenv("CDN_ANALYTICS_DB", str(tmp_path / "cdn.db"))
    import app.main as main
    main = importlib.reload(main)
    main.init_db()
    return main


def event(**overrides):
    value = {
        "region": "us-west",
        "provider": "vendor-a",
        "cache_hit": True,
        "bytes_sent": 1_000_000,
        "latency_ms": 40,
        "origin_bytes": 0,
    }
    value.update(overrides)
    return value


def test_empty_summary_is_zero(tmp_path, monkeypatch):
    main = module(tmp_path, monkeypatch)
    response = main.metrics_summary(region=None, provider=None)
    assert response.event_count == 0
    assert response.cache_hit_ratio == 0


def test_summary_calculates_cache_and_bandwidth_metrics(tmp_path, monkeypatch):
    main = module(tmp_path, monkeypatch)
    main.record_event(main.DeliveryEvent(**event()))
    main.record_event(main.DeliveryEvent(**event(cache_hit=False, bytes_sent=3_000_000, origin_bytes=3_000_000, latency_ms=80)))
    response = main.metrics_summary(region=None, provider=None)
    assert response.event_count == 2
    assert response.cache_hit_ratio == 0.5
    assert response.average_latency_ms == 60
    assert response.origin_traffic_gb == 0.003


def test_summary_filters_by_region_and_provider(tmp_path, monkeypatch):
    main = module(tmp_path, monkeypatch)
    main.record_event(main.DeliveryEvent(**event()))
    main.record_event(main.DeliveryEvent(**event(region="eu-west", provider="vendor-b")))
    response = main.metrics_summary(region="eu-west", provider="vendor-b")
    assert response.event_count == 1


def test_clear_events(tmp_path, monkeypatch):
    main = module(tmp_path, monkeypatch)
    main.record_event(main.DeliveryEvent(**event()))
    assert main.clear_events()["deleted"] == 1
