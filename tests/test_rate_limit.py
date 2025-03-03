"""Test script for rate limiting functionality."""
import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def make_request(session, request_num):
    """Make a single request and return the result."""
    start_time = time.time()
    try:
        async with session.post(
            'https://localhost:8000/research',
            json={"query": f"Test query {request_num}"},
            ssl=False,  # For self-signed cert
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            elapsed = time.time() - start_time
            status = response.status
            try:
                body = await response.json()
            except:
                try:
                    body = await response.text()
                except:
                    body = ""
            
            result = {
                "request_num": request_num,
                "status": status,
                "elapsed": elapsed,
                "body": body,
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")
            }
            
            # Print real-time status
            status_color = "\033[92m" if status == 200 else "\033[91m" if status == 429 else "\033[93m"
            print(f"{status_color}Request {request_num}: Status {status} at {result['timestamp']}\033[0m")
            if status == 429:
                if isinstance(body, dict) and 'detail' in body:
                    print(f"Rate limit message: {body['detail']}")
                else:
                    print(f"Rate limit response: {body}")
            
            return result
            
    except Exception as e:
        elapsed = time.time() - start_time
        error_result = {
            "request_num": request_num,
            "status": "error",
            "elapsed": elapsed,
            "body": f"Error: {str(e)}",
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")
        }
        print(f"\033[91mRequest {request_num}: Failed - {str(e)}\033[0m")
        return error_result

async def test_burst_limit():
    """Test the burst limit (10 requests per second)."""
    print("\n=== Testing Burst Limit (15 requests in 1 second) ===")
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, i) for i in range(15)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r["status"] == 200)
        rate_limited = sum(1 for r in results if r["status"] == 429)
        
        print(f"Successful requests: {success_count}")
        print(f"Rate limited requests: {rate_limited}")
        print("\nDetailed results:")
        for r in results:
            print(f"Request {r['request_num']}: Status {r['status']} at {r['timestamp']} ({r['elapsed']:.2f}s)")
            if r["status"] == 429:
                print(f"Rate limit message: {r['body']}")

async def test_minute_limit():
    """Test the per-minute limit (70 requests in 1 minute)."""
    print("\n=== Testing Minute Limit (70 requests spread over 60 seconds) ===")
    async with aiohttp.ClientSession() as session:
        results = []
        for i in range(70):
            result = await make_request(session, i)
            results.append(result)
            await asyncio.sleep(60/70)  # Spread requests over a minute
            
            print(f"Request {result['request_num']}: Status {result['status']} at {result['timestamp']}")
            if result["status"] == 429:
                print(f"Rate limit message: {result['body']}")
        
        success_count = sum(1 for r in results if r["status"] == 200)
        rate_limited = sum(1 for r in results if r["status"] == 429)
        
        print(f"\nFinal Results:")
        print(f"Successful requests: {success_count}")
        print(f"Rate limited requests: {rate_limited}")

async def main():
    """Run all tests."""
    print("Starting rate limit tests...")
    
    # Test 1: Burst Limit
    await test_burst_limit()
    
    # Wait a bit between tests
    print("\nWaiting 10 seconds before next test...")
    await asyncio.sleep(10)
    
    # Test 2: Minute Limit
    await test_minute_limit()

if __name__ == "__main__":
    asyncio.run(main())
