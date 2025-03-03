"""
Secure configuration file for sensitive data paths.
This file should never contain actual sensitive data, only paths to secure storage locations.
"""
import os

# Base paths
SECURE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'secure')

# SSL/TLS Certificates
SSL_CERT_PATH = os.path.join(SECURE_DIR, 'cert.pem')
SSL_KEY_PATH = os.path.join(SECURE_DIR, 'key.pem')

# Validation
def validate_secure_paths():
    """Validate that all secure paths exist and have correct permissions."""
    required_files = [
        (SSL_CERT_PATH, 0o600),
        (SSL_KEY_PATH, 0o600),
    ]
    
    for file_path, required_mode in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required secure file not found: {file_path}")
        
        # Check file permissions
        stat = os.stat(file_path)
        actual_mode = stat.st_mode & 0o777
        if actual_mode != required_mode:
            raise PermissionError(
                f"Incorrect permissions for {file_path}. "
                f"Expected: {oct(required_mode)}, Got: {oct(actual_mode)}"
            )
            
# Validate on import
validate_secure_paths()
