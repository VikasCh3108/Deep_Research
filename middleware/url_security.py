"""URL security middleware for validating and sanitizing URLs."""
from typing import Optional, List, Tuple
import re
import ipaddress
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote, unquote
import logging
import tldextract
import requests
from pydantic import BaseModel, HttpUrl
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import json

logger = logging.getLogger(__name__)

class URLValidator:
    def __init__(self):
        # List of allowed domains (can be expanded)
        self.allowed_domains = {
            # Code repositories
            'github.com', 'gitlab.com', 'bitbucket.org',
            
            # Academic sources
            'arxiv.org', 'wikipedia.org', 'scholar.google.com',
            'research.google.com', 'science.org', 'nature.com',
            'ieee.org', 'doi.org', 'springer.com', 'acm.org',
            'sciencedirect.com', 'jstor.org', 'ssrn.com',
            
            # Documentation
            'python.org', 'docs.python.org', 'readthedocs.io',
            'docs.scipy.org', 'numpy.org', 'pandas.pydata.org',
            'pytorch.org', 'tensorflow.org',
            
            # Package repositories
            'pypi.org', 'conda.io', 'anaconda.org',
            
            # Cloud platforms
            'aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com',
            
            # Development resources
            'stackoverflow.com', 'developer.mozilla.org'
        }
        
        # List of blocked TLDs and domains
        self.blocked_tlds = {
            'xyz', 'top', 'pw', 'tk', 'ml', 'cn', 'su',
            'download', 'zip', 'review', 'country', 'stream',
            'gdn', 'xin', 'loan', 'racing', 'party'
        }
        
        # Blocked IP ranges (CIDR notation)
        self.blocked_ip_ranges = [
            '10.0.0.0/8',      # Private network
            '172.16.0.0/12',   # Private network
            '192.168.0.0/16',  # Private network
            '127.0.0.0/8',     # Localhost
            '169.254.0.0/16',  # Link-local
            '0.0.0.0/8',       # Invalid addresses
            'fc00::/7',        # Unique local addresses
            'fe80::/10',       # Link-local addresses
        ]
        
        # Maximum URL length
        self.max_url_length = 2048
        
        # Tracking parameters to remove
        self.tracking_params = [
            'utm_', 'fbclid', 'gclid', '_ga',
            'ref', 'source', 'campaign', 'medium',
            'term', 'content', 'affiliate', '_hsenc',
            '_hsmi', 'mc_', 'mkt_', 'sb_'
        ]
        
        # List of blocked TLDs
        self.blocked_tlds = {'xyz', 'top', 'pw', 'tk', 'ml'}
        
        # Regex for potential malicious patterns
        self.malicious_patterns = [
            r'(eval\(|exec\(|system\()',  # Code execution
            r'(\.\./|\.\./\./)',  # Directory traversal
            r'(<script|javascript:)',  # XSS attempts
            r'(union.*select|select.*from)',  # SQL injection
        ]
        
        # Initialize session with security headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ResearchBot/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
        })
    
    def is_safe_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Check if a URL is safe to process.
        Returns (is_safe, reason_if_unsafe)
        """
        try:
            # Check URL length
            if not url or len(url) > self.max_url_length:
                return False, "URL exceeds maximum length"
            
            # Basic URL validation
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, "Invalid URL format"
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False, "Invalid URL scheme"
            
            # Extract domain info
            ext = tldextract.extract(url)
            domain = f"{ext.domain}.{ext.suffix}"
            
            # Check for IP address
            try:
                ip = ipaddress.ip_address(parsed.netloc)
                # Check if IP is in blocked ranges
                for ip_range in self.blocked_ip_ranges:
                    network = ipaddress.ip_network(ip_range)
                    if ip in network:
                        return False, f"IP in blocked range {ip_range}"
                return False, "Direct IP access not allowed"
            except ValueError:
                pass  # Not an IP address, continue with domain checks
            
            # Check TLD
            if ext.suffix in self.blocked_tlds:
                return False, "Blocked TLD"
            
            # Check for malicious patterns
            for pattern in self.malicious_patterns:
                if re.search(pattern, url, re.I):
                    return False, "Potentially malicious pattern detected"
            
            # Check for localhost attempts
            if any(x in parsed.netloc.lower() for x in ['localhost', '127.0.0.1', '[::1]']):
                return False, "Localhost access not allowed"
            
            # Check for user:pass in URL
            if '@' in parsed.netloc:
                return False, "Credentials in URL not allowed"
            
            # Check for common attack patterns
            if '..' in url or './.' in url:
                return False, "Directory traversal attempt detected"
            
            if re.search(r'(\\x[0-9a-fA-F]{2}|%[0-9a-fA-F]{2}){3,}', url):
                return False, "Excessive URL encoding detected"
            
            # Check domain against allowlist
            if domain not in self.allowed_domains:
                return False, f"Domain {domain} not in allowed list"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False, "URL validation error"
    
    def sanitize_url(self, url: str) -> str:
        """Sanitize a URL by removing potentially dangerous components."""
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Normalize scheme
            scheme = parsed.scheme.lower()
            
            # Normalize domain
            domain = parsed.netloc.lower()
            if '@' in domain:
                domain = domain.split('@')[1]  # Remove userinfo
            
            # Remove default ports
            if ':' in domain:
                host, port = domain.rsplit(':', 1)
                if (scheme == 'http' and port == '80') or \
                   (scheme == 'https' and port == '443'):
                    domain = host
            
            # Normalize path
            path = parsed.path
            if not path:
                path = '/'
            # Collapse multiple slashes and resolve dots
            path = re.sub(r'/+', '/', path)
            
            # Filter query parameters
            query = ''
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                # Remove tracking parameters
                filtered_params = {k: v for k, v in params.items()
                                if not any(t in k.lower() for t in self.tracking_params)}
                # Sort parameters for consistency
                query = urlencode(sorted(filtered_params.items()), doseq=True)
            
            # Rebuild URL without fragment
            parts = (scheme, domain, path, '', query, '')
            url = urlunparse(parts)
            
            # Decode unnecessary URL encoding
            url = unquote(url)
            
            # Re-encode only necessary characters
            return quote(url, safe=':/?=&%[]@!$\'()*+,;')
            
        except Exception as e:
            logger.error(f"Error sanitizing URL {url}: {str(e)}")
            return url
    
    async def validate_and_check_url(self, url: str) -> tuple[bool, Optional[str]]:
        """Validate URL and perform security checks."""
        # First check if URL is safe
        is_safe, reason = self.is_safe_url(url)
        if not is_safe:
            return False, reason
        
        try:
            # Sanitize URL
            sanitized_url = self.sanitize_url(url)
            
            # Perform a HEAD request to check URL without downloading content
            response = self.session.head(sanitized_url, timeout=5, allow_redirects=True)
            
            # Check response
            if response.status_code != 200:
                return False, f"URL returned status code {response.status_code}"
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith(('text/html', 'text/plain', 'application/pdf')):
                return False, "Unsupported content type"
            
            return True, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking URL {url}: {str(e)}")
            return False, "Failed to verify URL"

url_validator = URLValidator()

async def url_security_middleware(request: Request, call_next):
    """Middleware to handle URL security."""
    # Skip URL security for non-research endpoints
    if not request.url.path.startswith('/research'):
        return await call_next(request)
    
    try:
        # Get request body
        body = await request.json()
        urls = body.get('urls', [])
        
        # Track modifications
        url_changes = []
        blocked_urls = []
        
        # Process URLs
        sanitized_urls = []
        for url in urls:
            # Basic type check
            if not isinstance(url, str):
                blocked_urls.append((url, "URL must be a string"))
                continue
                
            # Check URL safety
            is_safe, message = url_validator.is_safe_url(url)
            if not is_safe:
                logger.warning(f"Blocked unsafe URL: {url}, Reason: {message}")
                blocked_urls.append((url, message))
                continue
            
            # Sanitize URL
            sanitized_url = url_validator.sanitize_url(url)
            sanitized_urls.append(sanitized_url)
            
            # Track changes
            if sanitized_url != url:
                url_changes.append({
                    "original": url,
                    "sanitized": sanitized_url,
                    "changes": [
                        "Removed tracking parameters" if any(p in url for p in url_validator.tracking_params) else None,
                        "Removed fragment" if '#' in url else None,
                        "Normalized URL" if url.lower() != url else None
                    ]
                })
        
        # If any URLs were blocked, return error with details
        if blocked_urls:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid URLs detected",
                    "blocked_urls": [
                        {"url": url, "reason": reason}
                        for url, reason in blocked_urls
                    ]
                }
            )
        
        # Update request body with sanitized URLs
        body['urls'] = sanitized_urls
        
        # Add security headers
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'"
        }
        
        # Create new request with updated body
        request._body = json.dumps(body).encode()
        
        # Process request
        response = await call_next(request)
        
        # Add security headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        # If URLs were modified, add info to response
        if url_changes:
            response.headers['X-URL-Changes'] = json.dumps(url_changes)
        
        return response
        
    except json.JSONDecodeError:
        return await call_next(request)
        
    except Exception as e:
        logger.error(f"Error in URL security middleware: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "URL security error",
                "detail": str(e)
            }
        )
