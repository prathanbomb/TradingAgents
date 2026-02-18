# External Integrations

**Analysis Date:** 2026-02-18

## APIs & External Services

**LLM Providers:**
- OpenAI - GPT models for agent reasoning
  - SDK/Client: langchain-openai
  - Models: gpt-4o (deep think), gpt-4o-mini (quick think)
  - Auth: `LLM_API_KEY` environment variable
  - Configuration: `LLM_PROVIDER=openai`

- Anthropic Claude - Alternative LLM provider
  - SDK/Client: langchain-anthropic
  - Auth: `LLM_API_KEY` environment variable
  - Configuration: `LLM_PROVIDER=anthropic`

- Google Gemini - Alternative LLM provider
  - SDK/Client: langchain-google-genai
  - Auth: `GOOGLE_API_KEY` environment variable
  - Configuration: `LLM_PROVIDER=gemini`
  - File: `tradingagents/dataflows/gemini.py`

- Custom OpenAI-compatible endpoints
  - SDK/Client: langchain-openai
  - Auth: `LLM_API_KEY`
  - Configuration: `LLM_BACKEND_URL` for custom endpoint

**Market Data Providers:**
- Yahoo Finance (yfinance) - Free market data
  - SDK/Client: yfinance library
  - Auth: None required
  - File: `tradingagents/dataflows/y_finance.py`, `tradingagents/dataflows/vendors/yfinance_vendor.py`

- Alpha Vantage - Stock data and news
  - SDK/Client: Custom implementation using requests
  - Auth: `ALPHA_VANTAGE_API_KEY`
  - Files: `tradingagents/dataflows/alpha_vantage*.py`, `tradingagents/dataflows/vendors/alpha_vantage_vendor.py`
  - Base: `tradingagents/dataflows/alpha_vantage_common.py`

- Google Search (via Gemini) - News with search grounding
  - SDK/Client: google-genai
  - Auth: `GOOGLE_API_KEY`
  - File: `tradingagents/dataflows/gemini.py`, `tradingagents/dataflows/vendors/google_vendor.py`

**Social Media:**
- Reddit - Sentiment analysis via PRAW
  - SDK/Client: praw (Python Reddit API Wrapper)
  - Auth: Reddit app credentials (not in .env.example)
  - File: `tradingagents/dataflows/reddit_utils.py`

**Additional Data Sources:**
- EODHD - Historical market data
  - SDK/Client: eodhd library
  - File: `tradingagents/dataflows/` (imported in vendor registry)

- Finnhub - Stock data and news
  - SDK/Client: finnhub-python
  - File: `tradingagents/dataflows/` (imported in vendor registry)

- Akshare - Chinese market data
  - SDK/Client: akshare library
  - File: `tradingagents/dataflows/` (imported in vendor registry)

- Tushare - Chinese stock data
  - SDK/Client: tushare library
  - File: `tradingagents/dataflows/` (imported in vendor registry)

## Data Storage

**Databases:**
- SQLite - Job queue and persistence
  - Connection: `DB_PATH` environment variable (default: ./data/jobs.db)
  - Client: Standard library sqlite3
  - File: `/Users/prathanbomb/Documents/workspace-python/trading-agents/data/jobs.db`

**File Storage:**
- Local filesystem - Primary report storage
  - Location: `REPORTS_OUTPUT_DIR` environment variable (default: ./reports)
  - File: `tradingagents/storage/backends/local.py`

- Cloudflare R2 (S3-compatible) - Cloud storage backup
  - Connection: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
  - Client: boto3 with S3-compatible API
  - Bucket: `R2_BUCKET_NAME`
  - File: `tradingagents/storage/backends/r2.py`

**Vector Storage:**
- ChromaDB - Agent memory embeddings
  - Connection: In-memory ephemeral instances
  - Client: chromadb
  - File: `tradingagents/agents/utils/memory.py`

**Caching:**
- Redis - Listed in requirements but no active usage found in codebase
  - Not currently implemented in tradingagents/

## Authentication & Identity

**Auth Provider:**
- Custom API key authentication
  - Implementation: TradingAgentsConfig validates API keys
  - File: `tradingagents/config/models.py`

**OAuth:**
- Google OAuth for Sheets/Docs access
  - Implementation: google-auth-oauthlib
  - Credentials: `GOOGLE_SHEETS_CREDENTIALS` (service account JSON)
  - File: `tradingagents/portfolio/google_sheets.py`

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Approach: Python standard logging with structured configuration
- File: `tradingagents/logging_config.py`
- Level: `LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR)
- Format: `LOG_FORMAT` environment variable (json or text)

**Notifications:**
- Discord webhooks - Analysis completion notifications
  - Implementation: HTTP POST to webhook URL
  - Configuration: `DISCORD_WEBHOOK_URL`
  - File: Not explicitly found in tradingagents/ (likely in scripts/)

## CI/CD & Deployment

**Hosting:**
- GitHub Actions - CI/CD pipeline
  - File: `.github/workflows/scheduled-analysis.yml`
  - OS: ubuntu-latest
  - Timeout: 120 minutes

**CI Pipeline:**
- Service: GitHub Actions
- Triggers:
  - Manual workflow_dispatch
  - External repository_dispatch via API
- Steps:
  1. Checkout repository
  2. Set up Python 3.12
  3. Install system dependencies (PDF generation libraries)
  4. Install Python dependencies (pip install -e .)
  5. Run scheduled analysis (scripts/run_scheduled_analysis.py)
  6. Upload reports as artifacts

**Job Queue:**
- SQLite-based job queue
  - Database: `data/jobs.db`
  - Configuration: `MAX_WORKERS`, `JOB_TIMEOUT`

## Environment Configuration

**Required env vars:**
- `LLM_PROVIDER` - openai, anthropic, gemini, ollama, openrouter, openai-compatible
- `LLM_API_KEY` - API key for chosen LLM provider
- `LLM_DEEP_THINK_MODEL` - Model for deep reasoning (default: gpt-4o)
- `LLM_QUICK_THINK_MODEL` - Model for quick tasks (default: gpt-4o-mini)

**Optional env vars:**
- `LLM_BACKEND_URL` - Custom endpoint URL for openai-compatible providers
- `EMBEDDING_PROVIDER` - same_as_llm, openai, gemini, local, disabled
- `EMBEDDING_MODEL` - Specific embedding model (auto-detect if empty)
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage API key
- `GOOGLE_API_KEY` - Google Gemini API key
- `TRADING_API_KEYS` - Comma-separated API keys for HTTP API access

**Storage configuration:**
- `R2_ACCOUNT_ID` - Cloudflare account ID
- `R2_ACCESS_KEY_ID` - R2 access key
- `R2_SECRET_ACCESS_KEY` - R2 secret key
- `R2_BUCKET_NAME` - R2 bucket name
- `R2_ENDPOINT_URL` - Custom R2 endpoint (auto-generated if not set)
- `R2_PUBLIC_URL` - Public URL base for permanent access
- `R2_PRESIGNED_URL_EXPIRY` - Presigned URL expiry in seconds (default: 3600)

**Portfolio Manager configuration:**
- `PORTFOLIO_MANAGER_ENABLED` - Enable portfolio-aware recommendations
- `GOOGLE_SHEETS_CREDENTIALS` - Path to Google service account credentials JSON
- `GOOGLE_SHEET_ID` - Google Sheet ID for portfolio storage
- `GOOGLE_SHEET_NAME` - Sheet name (default: "Trading Portfolio")
- `PORTFOLIO_MAX_POSITION_SIZE` - Max position size as percentage (default: 0.20)
- `PORTFOLIO_MIN_CASH_RESERVE` - Min cash reserve as percentage (default: 0.10)

**Secrets location:**
- Environment variables loaded from `.env` file via python-dotenv
- GitHub Actions secrets for CI/CD
- File: `.env.example` shows all available configuration options

## Webhooks & Callbacks

**Incoming:**
- GitHub repository_dispatch - External API trigger for analysis
  - Types: [run-analysis]
  - Payload: Can include tickers override

**Outgoing:**
- Discord webhook - Analysis completion notifications
  - Configuration: `DISCORD_WEBHOOK_URL`
  - Trigger: When analysis completes (configured in GitHub Actions)

---

*Integration audit: 2026-02-18*
