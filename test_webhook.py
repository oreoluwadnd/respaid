"""
Test idempotent webhook processing
Run: poetry run pytest test_webhook.py -v
"""
import pytest
from webhook.handler import process_webhook, create_payment
import fakeredis

# Use fake Redis for testing - no external deps
fake_redis = fakeredis.FakeRedis(decode_responses=True)

@pytest.fixture(autouse=True)
def setup_redis(monkeypatch):
    """Inject fake Redis into handler module"""
    monkeypatch.setattr('webhook.handler.redis_client', fake_redis)
    fake_redis.flushall()  # Clean slate for each test
    yield
    fake_redis.flushall()

@pytest.fixture
def mock_payment(mocker):
    """Mock the payment creation"""
    mock = mocker.patch('webhook.handler.create_payment')
    mock.return_value = type('Transaction', (), {'id': 'txn_test123'})()
    return mock


def test_duplicate_webhook_ignored(mock_payment):
    """Idempotent: duplicate event_id should return cached result"""
    
    # First call processes payment
    result1 = process_webhook(event_id="evt_123", amount=5000)
    assert result1["status"] == "success"
    assert result1["transaction_id"] == "txn_test123"
    assert mock_payment.call_count == 1
    
    # Second call returns cached, doesn't process again
    result2 = process_webhook(event_id="evt_123", amount=5000)
    assert result2["status"] == "already_processed"
    assert result2["event_id"] == "evt_123"
    assert mock_payment.call_count == 1  # Still 1! Not called again


def test_webhook_caches_failures(mocker):
    """Failed webhooks should be cached to prevent retry storms"""
    mocker.patch(
        'webhook.handler.create_payment',
        side_effect=Exception("Payment gateway timeout")
    )
    
    # First call fails
    with pytest.raises(Exception, match="Payment gateway timeout"):
        process_webhook(event_id="evt_456", amount=1000)
    
    # Verify failure is cached (check Redis directly)
    cached_value = fake_redis.get("webhook:evt_456")
    assert cached_value is not None
    # Convert to string if bytes, then check content
    cached_str = cached_value.decode('utf-8') if isinstance(cached_value, bytes) else str(cached_value)  # type: ignore
    assert "failed" in cached_str
    
    # Verify TTL is set (should be 3600s for failures)
    ttl = fake_redis.ttl("webhook:evt_456")
    # FakeRedis returns int directly, but handle any type conversion
    try:
        ttl_value = int(ttl)  # type: ignore
    except (ValueError, TypeError):
        ttl_value = -1
    assert ttl_value > 0 and ttl_value <= 3600


def test_different_events_processed_separately(mock_payment):
    """Different event IDs should be processed independently"""
    result1 = process_webhook(event_id="evt_001", amount=1000)
    result2 = process_webhook(event_id="evt_002", amount=2000)
    
    assert result1["status"] == "success"
    assert result2["status"] == "success"
    assert mock_payment.call_count == 2  # Both processed