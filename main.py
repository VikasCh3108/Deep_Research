"""
Main application entry point.
"""
import uvicorn
import logging.config
from fastapi import FastAPI
from api.routes import app
from dotenv import load_dotenv
from config.logging_config import LOGGING_CONFIG
from middleware.rate_limiter import rate_limit_middleware
from middleware.url_security import url_security_middleware

# Load environment variables
load_dotenv()

# Initialize logging configuration
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Add middleware
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(url_security_middleware)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com;"
    return response

if __name__ == "__main__":
    try:
        from config.secure_config import SSL_KEY_PATH, SSL_CERT_PATH, validate_secure_paths
        
        # Validate secure paths before starting server
        validate_secure_paths()
        
        logger.info("Starting AI Agentic System server with security features")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_config=None,  # Disable uvicorn's default logging
            ssl_keyfile=SSL_KEY_PATH,  # Use secure path for SSL key
            ssl_certfile=SSL_CERT_PATH  # Use secure path for SSL cert
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
