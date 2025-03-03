"""Test URL security middleware with various URL patterns."""
import aiohttp
import asyncio
from datetime import datetime
import json

# Test URLs - mix of valid and potentially malicious ones
TEST_URLS = [
    # Valid URLs
    "https://www.example.com/article",
    "https://api.github.com/repos/user/repo",
    "https://docs.python.org/3/library/",
    
    # URLs with query parameters
    "https://example.com/search?q=test&page=1",
    "https://api.example.com/v1/users?include=profile,settings",
    
    # URLs with tracking parameters (should be sanitized)
    "https://example.com/product?utm_source=google&utm_medium=cpc",
    "https://shop.com/item?fbclid=123&ref=social",
    
    # URLs with fragments (should be removed)
    "https://docs.example.com/guide#section-1",
    "https://app.com/dashboard#/settings/profile",
    
    # Potentially malicious URLs
    "file:///etc/passwd",  # Local file access attempt
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata endpoint
    "https://evil.com/script.php?cmd=rm%20-rf%20/",  # Command injection attempt
    "javascript:alert('xss')",  # XSS attempt
    "data:text/html,<script>alert('xss')</script>",  # Data URL scheme
    "https://example.com@evil.com",  # URL confusion
    "https://evil.com/redirect?url=http://internal-network/admin",  # SSRF attempt
    
    # Invalid or malformed URLs
    "not_a_url",
    "http://",
    "https://.com",
    "http://example.com:abc",  # Invalid port
    
    # URLs with special characters
    "https://example.com/path with spaces",
    "https://example.com/path/with/émojis/🔒",
    "https://example.com/path%20encoded",
]

async def test_url(session, url: str) -> dict:
    """Test a single URL against the security middleware."""
    try:
        start_time = datetime.now()
        async with session.post(
            'https://localhost:8000/research',
            json={"query": f"Research about: {url}", "urls": [url]},
            ssl=False,  # For self-signed cert
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            status = response.status
            try:
                body = await response.json()
            except:
                body = await response.text()
                
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                "url": url,
                "status": status,
                "response": body,
                "elapsed": elapsed
            }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "response": str(e),
            "elapsed": (datetime.now() - start_time).total_seconds()
        }

def print_result(result: dict):
    """Print a formatted test result."""
    status_color = (
        "\033[92m" if result["status"] == 200 
        else "\033[91m" if result["status"] in [400, 403] 
        else "\033[93m"
    )
    print(f"\n{status_color}Testing URL: {result['url']}")
    print(f"Status: {result['status']}")
    print(f"Response: {json.dumps(result['response'], indent=2)}")
    print(f"Time: {result['elapsed']:.2f}s\033[0m")

async def main():
    """Run URL security tests."""
    print("\n=== Starting URL Security Tests ===\n")
    
    async with aiohttp.ClientSession() as session:
        # Test each URL sequentially to avoid rate limiting
        results = []
        for url in TEST_URLS:
            result = await test_url(session, url)
            results.append(result)
            print_result(result)
            await asyncio.sleep(1)  # Delay between requests
        
        # Print summary
        print("\n=== Test Summary ===")
        total = len(results)
        allowed = sum(1 for r in results if r["status"] == 200)
        blocked = sum(1 for r in results if r["status"] in [400, 403])
        errors = sum(1 for r in results if r["status"] not in [200, 400, 403])
        
        print(f"\nTotal URLs tested: {total}")
        print(f"Allowed URLs: {allowed}")
        print(f"Blocked URLs: {blocked}")
        print(f"Errors: {errors}")

if __name__ == "__main__":
    asyncio.run(main())
