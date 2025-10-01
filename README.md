# Respaid - Webhook Handler

A Python-based webhook handler that processes payment events with Redis-backed idempotency to prevent duplicate processing.

## Features

- **Idempotent Processing**: Uses Redis caching to ensure webhook events are processed only once
- **Payment Gateway Integration**: Simulates payment creation (easily extensible to real payment providers)
- **Error Handling**: Caches failures to prevent retry storms
- **TTL-based Caching**: Different cache expiration times for successful and failed events

## Project Structure

```
respaid/
├── webhook/
│   ├── __init__.py
│   └── handler.py          # Main webhook processing logic
├── test_webhook.py         # Test suite
├── pyproject.toml         # Poetry configuration
├── poetry.lock           # Dependency lock file
└── README.md            # This file
```

## Requirements

- Python 3.8+
- Redis server running on localhost:6379
- Poetry for dependency management

## Installation

1. Install dependencies using Poetry:
```bash
poetry install
```

2. Start Redis server:
```bash
redis-server
```

## Usage

### Basic Usage

```python
from webhook.handler import process_webhook

# Process a webhook event
result = process_webhook(event_id="evt_123", amount=1000)
print(result)
# Output: {"status": "success", "transaction_id": "txn_1000"}

# Subsequent calls with same event_id return cached result
result = process_webhook(event_id="evt_123", amount=1000)
print(result)
# Output: {"status": "already_processed", "event_id": "evt_123"}
```

### Function Details

#### `process_webhook(event_id: str, amount: int) -> Dict[str, Any]`

Processes webhook events idempotently using Redis cache.

**Parameters:**
- `event_id` (str): Unique identifier for the webhook event
- `amount` (int): Payment amount to process

**Returns:**
- Dict containing processing status and relevant data

**Possible Return Values:**
- Success: `{"status": "success", "transaction_id": "txn_<amount>"}`
- Already processed: `{"status": "already_processed", "event_id": "<event_id>"}`
- Raises exception on failure (failure is cached to prevent retry storms)

## Caching Strategy

- **Successful events**: Cached for 24 hours (86400 seconds)
- **Failed events**: Cached for 1 hour (3600 seconds) to prevent retry storms
- **Cache key format**: `webhook:<event_id>`

## Testing

Run the test suite:

```bash
poetry run pytest test_webhook.py -v
```

Test coverage includes:
- Successful payment processing
- Idempotency verification
- Error handling and caching
- Redis interaction

## Configuration

### Redis Configuration

The Redis client is configured in `webhook/handler.py`:

```python
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=False
)
```

You can modify these settings for different environments:
- Development: Use localhost Redis
- Production: Use Redis cluster or managed Redis service
- Testing: Use separate Redis database (e.g., `db=1`)

## Error Handling

The webhook handler implements robust error handling:

1. **Network failures**: Cached to prevent immediate retries
2. **Payment gateway errors**: Logged and cached with shorter TTL
3. **Redis failures**: Application will fail fast (no silent failures)

## Development

### Adding New Payment Providers

To integrate with real payment providers, modify the `create_payment` function:

```python
def create_payment(amount: int) -> Any:
    response = payment_provider.create_charge(amount=amount)
    return response
```

### Environment Variables

Consider adding environment variables for:
- Redis connection details
- Payment provider API keys
- Cache TTL values
- Debug/logging levels

## Security Considerations

- Validate webhook signatures in production
- Use HTTPS for webhook endpoints
- Implement rate limiting
- Store sensitive data (API keys) in environment variables
- Use Redis AUTH in production environments

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions, please open an issue in the repository.