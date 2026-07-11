import asyncio
import sys
sys.path.insert(0, '.')

# Directly test the RateLimiter
async def test():
    from app.core.dependencies import auth_rate_limiter
    from app.core.redis import get_redis_client
    r = get_redis_client()
    
    # Test if pipeline works with the rate limiter
    import time
    key = 'test:ratelimit'
    now = int(time.time())
    window_start = now - 60
    
    pipe = r.pipeline(transaction=True)
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 60)
    results = await pipe.execute()
    print('Pipeline works! Results:', results)

asyncio.run(test())
