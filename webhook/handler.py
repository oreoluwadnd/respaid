import redis
from typing  import Dict , Any




redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)




def create_payment(amount: int) -> Any:
   """Simulate payment creation with a payment gateway"""
   # In real life, this would call an external API
   return type('Transaction', (), {
       'id': f'txn_{amount}',
       'amount': amount,
       'status': 'succeeded'
   })()


def process_webhook(event_id: str, amount: int) -> Dict[str, Any]:
    """
    Process webhook events idempotently using Redis cache.
    
    Args:
        event_id: Unique identifier for the webhook event
        amount: Payment amount to process
        
    Returns:
        Dict containing processing status and relevant data
    """
    import json
    
    # Check if event was already processed
    cache_key = f"webhook:{event_id}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        # Event already processed, return cached result
        # Decode bytes to string since decode_responses=False
        cached_str = cached_result.decode('utf-8') if isinstance(cached_result, bytes) else str(cached_result)
        cached_data = json.loads(cached_str)
        if cached_data.get("status") == "failed":
            # Re-raise the cached failure
            raise Exception(cached_data.get("error", "Previous processing failed"))
        return {
            "status": "already_processed",
            "event_id": event_id
        }
    
    try:
        # Process the payment
        transaction = create_payment(amount)
        
        # Cache successful result (with reasonable TTL, e.g., 24 hours)
        result = {
            "status": "success",
            "transaction_id": transaction.id
        }
        redis_client.setex(cache_key, 86400, json.dumps(result))
        
        return result
        
    except Exception as e:
        # Cache failure to prevent retry storms (shorter TTL, e.g., 1 hour)
        failure_data = {
            "status": "failed",
            "error": str(e)
        }
        redis_client.setex(cache_key, 3600, json.dumps(failure_data))
        
        # Re-raise the exception
        raise