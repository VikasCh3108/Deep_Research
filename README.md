# Deep Research AI Agentic System

An advanced multi-agent system for conducting deep research and information gathering using LangChain and LangGraph frameworks.

## System Architecture

The system consists of multiple specialized agents working together:

### Core Agents
1. **Research Agent**: Responsible for web crawling, data collection, and information gathering using Tavily API
2. **Synthesis Agent**: Processes and synthesizes collected information into coherent answers

### Specialized Agents
3. **Citation Agent**: Manages and validates citations, ensuring proper attribution and reference formatting
4. **Code Analysis Agent**: Analyzes code snippets and repositories, providing technical insights
5. **Data Analysis Agent**: Processes and analyzes structured data, generating insights and visualizations
6. **Fact Checking Agent**: Verifies claims and statements against reliable sources
7. **Query Refinement Agent**: Improves search queries for better research results

All agents communicate through the orchestrator, which manages task distribution and coordination.

### Key Features
- Multi-agent coordination using LangGraph
- Web crawling and information gathering with Tavily
- Structured data processing and storage
- Answer synthesis and formatting
- REST API interface for system interaction
- Robust URL security and validation
- Rate limiting and request throttling
- Comprehensive security logging

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```env
# API Keys
TAVILY_API_KEY=your_tavily_api_key
OPENAI_API_KEY=your_openai_api_key

# Security Settings
SECRET_KEY=your_secret_key
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=False

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
BURST_LIMIT=100

# SSL Configuration
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

4. Generate SSL certificates (for HTTPS):
```bash
openssl req -x509 -newkey rsa:4096 -keyout config/secure/key.pem -out config/secure/cert.pem -days 365 -nodes
```

## Project Structure

```
ai_agentic_system/
├── agents/                 # AI Agents
│   ├── research_agent.py      # Web research and data collection
│   ├── synthesis_agent.py     # Information synthesis
│   ├── citation_agent.py      # Citation management
│   ├── code_analysis_agent.py # Code analysis
│   ├── data_analysis_agent.py # Data processing
│   ├── fact_checking_agent.py # Fact verification
│   └── query_refinement_agent.py # Query optimization
├── core/                  # Core System Components
│   ├── orchestrator.py       # Agent coordination
│   └── types.py             # Type definitions
├── api/                   # API Layer
│   └── routes.py            # API endpoints
├── middleware/            # Request Processing
│   ├── rate_limiter.py      # Rate limiting
│   └── url_security.py      # URL validation
├── config/                # Configuration
│   ├── logging_config.py    # Logging setup
│   ├── secure_config.py     # Security settings
│   └── secure/             # SSL certificates
├── utils/                 # Utilities
│   └── helpers.py           # Helper functions
├── logs/                  # System Logs
│   ├── api_YYYYMMDD.log     # API activity
│   ├── research_YYYYMMDD.log # Research tasks
│   └── error_YYYYMMDD.log   # Error tracking
├── tests/                 # Test Suite
│   ├── test_agents/         # Agent tests
│   ├── test_api/           # API tests
│   └── test_security/      # Security tests
├── docs/                  # Documentation
│   ├── api/                # API documentation
│   └── architecture/       # System design docs
├── templates/             # Web Templates
│   └── index.html          # Main interface
├── static/                # Static Assets
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript files
├── main.py               # Application entry
├── requirements.txt      # Dependencies
└── README.md            # Project documentation
```
```

## Usage

1. Start the system:
```bash
uvicorn main:app --reload
```

2. Access the web interface at `http://localhost:8000`

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_agents/
pytest tests/test_api/
pytest tests/test_security/

# Run with coverage report
pytest --cov=. tests/
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Documentation
```bash
# Generate API documentation
pip install pdoc3
pdoc --html --output-dir docs/api ai_agentic_system
```

## API Endpoints

### Research Operations
- `POST /research`: Submit a research query
- `GET /status/{task_id}`: Check research task status
- `GET /results/{task_id}`: Get research results

### Agent Management
- `GET /agents`: List available agents
- `GET /agents/{agent_id}/status`: Check agent status
- `POST /agents/{agent_id}/tasks`: Assign task to agent

### System Operations
- `GET /health`: System health check
- `GET /metrics`: System metrics and statistics
- `GET /logs`: Access system logs (admin only)

## Security Features

### URL Security
- Comprehensive URL validation and sanitization
- Whitelisted domains for research queries
- Protection against:
  - File system access attempts
  - Internal network access
  - XSS and injection attacks
  - Malicious redirects
  - Credential exposure in URLs

### Rate Limiting
- Request rate limiting per client
- Burst request protection
- Configurable rate limits

### Logging and Monitoring
- Detailed security event logging
- Request/response logging
- Error tracking and monitoring
- Log rotation with timestamps

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy: default-src 'self'
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000

## Security Configuration

The system includes several security-related configurations:

1. **URL Validation**:
   - Configure allowed domains in `middleware/url_security.py`
   - Add blocked TLDs and IP ranges
   - Set maximum URL length

2. **Rate Limiting**:
   - Configure limits in `middleware/rate_limiter.py`
   - Set requests per minute
   - Set burst request limits

3. **Logging**:
   - Configure log paths in `config/logging_config.py`
   - Set log rotation policies
   - Configure log levels for different components
