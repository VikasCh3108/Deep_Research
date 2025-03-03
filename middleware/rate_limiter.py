"""Rate limiting middleware for the API."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Tuple
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}
        self.block_duration = 300  # 5 minutes block
        logger.info(f"Initialized RateLimiter with {requests_per_minute} requests/minute, burst limit {burst_limit}")
        
    def is_rate_limited(self, ip: str) -> Tuple[bool, str]:
        """Check if the IP is rate limited."""
        current_time = time.time()
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            if current_time - self.blocked_ips[ip] < self.block_duration:
                remaining = int(self.block_duration - (current_time - self.blocked_ips[ip]))
                return True, f"Too many requests. Please try again in {remaining} seconds."
            else:
                del self.blocked_ips[ip]
        
        # Clean old requests
        self.requests[ip] = [req_time for req_time in self.requests[ip] 
                           if current_time - req_time < 60]
        
        # Check burst limit
        if len(self.requests[ip]) >= self.burst_limit:
            recent_requests = [req_time for req_time in self.requests[ip] 
                             if current_time - req_time < 1]
            if len(recent_requests) >= self.burst_limit:
                self.blocked_ips[ip] = current_time
                return True, "Too many requests in a short time. Please slow down."
        
        # Check rate limit
        if len(self.requests[ip]) >= self.requests_per_minute:
            self.blocked_ips[ip] = current_time
            return True, "Rate limit exceeded. Please try again later."
        
        self.requests[ip].append(current_time)
        return False, ""

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Middleware to handle rate limiting."""
    try:
        # Get client IP
        client_ip = request.client.host
        logger.debug(f"Processing request from IP: {client_ip}, Path: {request.url.path}")
        
        # Skip rate limiting for certain paths
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            logger.debug(f"Skipping rate limit for path: {request.url.path}")
            return await call_next(request)
        
        # Check rate limit
        is_limited, message = rate_limiter.is_rate_limited(client_ip)
        if is_limited:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}, Message: {message}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": message,
                    "type": "rate_limit_exceeded"
                }
            )
        
        # Process request
        logger.debug(f"Request allowed for IP: {client_ip}")
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Error in rate limit middleware: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error in rate limiter",
                "type": "internal_error"
            }
        )
