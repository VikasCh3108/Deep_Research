"""Logging configuration for the AI Agentic System."""
import os
import logging.config
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate log filenames with timestamp
TIMESTAMP = datetime.now().strftime('%Y%m%d')
LOG_FILES = {
    'api': os.path.join(LOGS_DIR, f'api_{TIMESTAMP}.log'),
    'research': os.path.join(LOGS_DIR, f'research_{TIMESTAMP}.log'),
    'synthesis': os.path.join(LOGS_DIR, f'synthesis_{TIMESTAMP}.log'),
    'orchestrator': os.path.join(LOGS_DIR, f'orchestrator_{TIMESTAMP}.log'),
    'error': os.path.join(LOGS_DIR, f'error_{TIMESTAMP}.log')
}

# Logging configuration dictionary
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'api_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': LOG_FILES['api'],
            'mode': 'a'
        },
        'research_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': LOG_FILES['research'],
            'mode': 'a'
        },
        'synthesis_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': LOG_FILES['synthesis'],
            'mode': 'a'
        },
        'orchestrator_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': LOG_FILES['orchestrator'],
            'mode': 'a'
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': LOG_FILES['error'],
            'mode': 'a'
        }
    },
    'loggers': {
        'api': {
            'level': 'DEBUG',
            'handlers': ['console', 'api_file', 'error_file'],
            'propagate': False
        },
        'agents.research_agent': {
            'level': 'DEBUG',
            'handlers': ['console', 'research_file', 'error_file'],
            'propagate': False
        },
        'agents.synthesis_agent': {
            'level': 'DEBUG',
            'handlers': ['console', 'synthesis_file', 'error_file'],
            'propagate': False
        },
        'core.orchestrator': {
            'level': 'DEBUG',
            'handlers': ['console', 'orchestrator_file', 'error_file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'error_file']
    }
}
