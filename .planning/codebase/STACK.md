# Technology Stack

**Analysis Date:** 2026-02-18

## Languages

**Primary:**
- Python 3.10+ - Core application language, required by setup.py
- Python 3.12 - Development and CI environment

**Secondary:**
- YAML - Configuration files (GitHub Actions)
- Markdown - Documentation and report generation

## Runtime

**Environment:**
- Python 3.10+ (production minimum)
- Python 3.12 (development and CI)

**Package Manager:**
- pip - Standard Python package manager
- Lockfile: `uv.lock` present (using uv package manager for faster dependency resolution)

## Frameworks

**Core:**
- LangChain 0.1.0+ - LLM orchestration framework for agent communication
- LangGraph 0.4.8+ - Graph-based agent workflow and state management
- LangChain OpenAI 0.3.23+ - OpenAI LLM integration
- LangChain Anthropic 0.3.15+ - Anthropic Claude integration
- LangChain Google GenAI 2.1.5+ - Google Gemini integration
- LangChain Experimental 0.3.4+ - Experimental LangChain features

**Data Processing:**
- Pandas 2.3.0+ - Data manipulation and analysis
- NumPy 1.24.0+ - Numerical computing

**Testing:**
- pytest - Test framework (inferred from tests/ directory and conftest.py)

**Build/Dev:**
- setuptools 80.9.0+ - Package building and distribution
- pyproject.toml - Modern Python project configuration

## Key Dependencies

**Critical:**
- pydantic - Data validation and settings management (used in config/models.py)
- python-dotenv 1.0.0+ - Environment variable loading from .env files

**Data Sources:**
- yfinance 0.2.63+ - Yahoo Finance API for market data
- praw 7.8.1+ - Reddit API for sentiment analysis
- stockstats 0.6.5+ - Technical indicator calculations
- eodhd 1.0.32+ - EOD Historical Data API
- backtrader 1.9.78.123+ - Backtesting framework
- akshare 1.16.98+ - Chinese market data
- tushare 1.4.21+ - Chinese stock data
- finnhub-python 2.4.23+ - Finnhub API
- feedparser 6.0.11+ - RSS/Atom feed parsing
- parsel 1.10.0+ - Web scraping utilities

**Vector Storage:**
- chromadb 1.0.12+ - Vector database for agent memory embeddings

**Cloud Storage:**
- boto3 1.26.0+ - AWS SDK for S3-compatible storage (Cloudflare R2)

**Report Generation:**
- weasyprint 60.0+ - HTML to PDF conversion
- markdown 3.5+ - Markdown processing

**Google Services:**
- google-api-python-client 2.100.0+ - Google API client
- google-auth-httplib2 0.1.0+ - Google authentication
- google-auth-oauthlib 1.0.0+ - Google OAuth support

**CLI/UX:**
- typer 0.9.0+ - CLI framework (inferred from setup.py)
- rich 13.0.0+ - Terminal formatting
- questionary 2.0.1+ - Interactive prompts

**Utilities:**
- requests 2.32.4+ - HTTP client library
- tqdm 4.67.1+ - Progress bars
- pytz 2025.2+ - Timezone handling

## Configuration

**Environment:**
- Configuration via python-dotenv from `.env` file
- Pydantic models for validation (tradingagents/config/models.py)
- Environment-based provider switching (LLM, embeddings, data vendors)

**Build:**
- `pyproject.toml` - Modern Python project configuration
- `setup.py` - Legacy setup script for package installation
- `requirements.txt` - Simple dependency listing
- `uv.lock` - UV package manager lockfile

**Entry Points:**
- Console script: `tradingagents=cli.main:app` (defined in setup.py)

## Platform Requirements

**Development:**
- Python 3.10+
- Virtual environment support (.venv directory present)
- pip or uv package manager

**Production:**
- Ubuntu/Linux environment (per GitHub Actions workflow)
- System dependencies for PDF generation:
  - libpango-1.0-0
  - libpangocairo-1.0-0
  - libgdk-pixbuf2.0-0
  - libffi-dev
  - shared-mime-info

---

*Stack analysis: 2026-02-18*
