"""Pydantic configuration models for TradingAgents."""

import os
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


LLMProvider = Literal["openai", "anthropic", "google", "openrouter", "ollama", "openai-compatible"]
EmbeddingProvider = Literal["same_as_llm", "openai", "gemini", "local", "disabled"]
StockVendor = Literal["yfinance", "alpha_vantage", "local"]
IndicatorVendor = Literal["yfinance", "alpha_vantage", "local"]
FundamentalVendor = Literal["yfinance", "openai", "alpha_vantage", "local"]
NewsVendor = Literal["openai", "alpha_vantage", "google", "local"]
StorageBackendType = Literal["local", "r2"]


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: LLMProvider = "openai"
    deep_think_model: str = "o4-mini"
    quick_think_model: str = "gpt-4o-mini"
    backend_url: str = "https://api.openai.com/v1"
    api_key_env_var: str = "OPENAI_API_KEY"

    @field_validator("backend_url")
    @classmethod
    def validate_backend_url(cls, v: str, info) -> str:
        """Ensure backend URL doesn't have trailing slash."""
        return v.rstrip("/")


class EmbeddingConfig(BaseModel):
    """Embedding provider configuration."""

    provider: EmbeddingProvider = "same_as_llm"
    model: Optional[str] = None
    backend_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    disabled: bool = False

    @model_validator(mode="after")
    def check_disabled_consistency(self) -> "EmbeddingConfig":
        """Ensure disabled flag is consistent with provider."""
        if self.provider == "disabled":
            self.disabled = True
        return self


class DataVendorConfig(BaseModel):
    """Data vendor configuration."""

    core_stock_apis: StockVendor = "yfinance"
    technical_indicators: IndicatorVendor = "yfinance"
    fundamental_data: FundamentalVendor = "yfinance"
    news_data: NewsVendor = "alpha_vantage"
    tool_overrides: Dict[str, str] = Field(default_factory=dict)

    @field_validator("tool_overrides")
    @classmethod
    def validate_tool_overrides(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate tool override vendor names."""
        valid_vendors = {
            "yfinance", "alpha_vantage", "local", "openai", "google"
        }
        for tool, vendor in v.items():
            if vendor not in valid_vendors:
                raise ValueError(f"Invalid vendor '{vendor}' for tool '{tool}'")
        return v


class PathConfig(BaseModel):
    """Path configuration with dynamic defaults."""

    project_dir: Path = Field(default=None)
    results_dir: Path = Field(default=None)
    data_dir: Optional[Path] = None
    data_cache_dir: Path = Field(default=None)

    @model_validator(mode="after")
    def set_default_paths(self) -> "PathConfig":
        """Set default paths based on module location."""
        module_dir = Path(__file__).parent.parent

        if self.project_dir is None:
            self.project_dir = module_dir

        if self.results_dir is None:
            env_results = os.getenv("TRADINGAGENTS_RESULTS_DIR")
            self.results_dir = Path(env_results) if env_results else Path("./results")

        if self.data_cache_dir is None:
            self.data_cache_dir = self.project_dir / "dataflows" / "data_cache"

        if self.data_dir is None:
            self.data_dir = self.project_dir / "dataflows" / "data"

        return self


class DebateConfig(BaseModel):
    """Debate and discussion configuration."""

    max_debate_rounds: int = Field(default=1, ge=1, le=10)
    max_risk_discuss_rounds: int = Field(default=1, ge=1, le=10)
    max_recur_limit: int = Field(default=100, ge=1)


class GoogleSheetsConfig(BaseModel):
    """Google Sheets portfolio storage configuration."""

    credentials_path: Optional[str] = Field(default=None)
    sheet_id: Optional[str] = Field(default=None)
    sheet_name: str = Field(default="Trading Portfolio")

    @property
    def is_configured(self) -> bool:
        """Check if all required Google Sheets settings are present."""
        return all([
            self.credentials_path,
            self.sheet_id,
        ])

    @classmethod
    def from_env(cls) -> "GoogleSheetsConfig":
        """Create Google Sheets config from environment variables."""
        return cls(
            credentials_path=os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
            sheet_id=os.getenv("GOOGLE_SHEET_ID"),
            sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Trading Portfolio"),
        )


class R2StorageConfig(BaseModel):
    """Cloudflare R2 storage configuration."""

    account_id: Optional[str] = Field(default=None)
    access_key_id: Optional[str] = Field(default=None)
    secret_access_key: Optional[str] = Field(default=None)
    bucket_name: Optional[str] = Field(default=None)
    endpoint_url: Optional[str] = Field(default=None)
    presigned_url_expiry: int = Field(default=3600, ge=60, le=604800)
    public_url: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def build_endpoint_url(self) -> "R2StorageConfig":
        """Build endpoint URL from account_id if not provided."""
        if self.endpoint_url is None and self.account_id:
            self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        return self

    @property
    def is_configured(self) -> bool:
        """Check if all required R2 settings are present."""
        return all([
            self.account_id or self.endpoint_url,
            self.access_key_id,
            self.secret_access_key,
            self.bucket_name,
        ])

    @classmethod
    def from_env(cls) -> "R2StorageConfig":
        """Create R2 config from environment variables."""
        return cls(
            account_id=os.getenv("R2_ACCOUNT_ID"),
            access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            bucket_name=os.getenv("R2_BUCKET_NAME"),
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            presigned_url_expiry=int(os.getenv("R2_PRESIGNED_URL_EXPIRY", "3600")),
            public_url=os.getenv("R2_PUBLIC_URL"),
        )


class TLDRStyle(str):
    """TL;DR style options."""
    COMPACT = "compact"
    DETAILED = "detailed"


class StorageConfig(BaseModel):
    """Storage configuration."""

    local_path: Optional[Path] = Field(default=None)
    r2: Optional[R2StorageConfig] = Field(default=None)
    include_tldr: bool = Field(default=True, description="Include TL;DR summary at the top of reports")
    tldr_style: Literal["compact", "detailed"] = Field(default="compact", description="TL;DR summary style")

    @model_validator(mode="after")
    def set_defaults(self) -> "StorageConfig":
        """Set default local path from environment."""
        if self.local_path is None:
            env_path = os.getenv("REPORTS_OUTPUT_DIR")
            self.local_path = Path(env_path) if env_path else Path("./reports")
        return self

    @property
    def is_r2_enabled(self) -> bool:
        """Check if R2 storage is configured and enabled."""
        return self.r2 is not None and self.r2.is_configured

    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Create storage config from environment variables."""
        r2_config = R2StorageConfig.from_env()
        return cls(
            local_path=Path(os.getenv("REPORTS_OUTPUT_DIR", "./reports")),
            r2=r2_config if r2_config.is_configured else None,
        )


class PortfolioManagerConfig(BaseModel):
    """Portfolio Manager configuration."""

    enabled: bool = Field(default=False)
    google_sheets: Optional[GoogleSheetsConfig] = Field(default=None)
    max_position_size: float = Field(default=0.20, ge=0.01, le=1.0, description="Max position size as percentage of portfolio")
    min_cash_reserve: float = Field(default=0.10, ge=0.0, le=1.0, description="Min cash reserve as percentage of portfolio")

    @model_validator(mode="after")
    def check_google_sheets_consistency(self) -> "PortfolioManagerConfig":
        """Ensure Google Sheets config is present if enabled."""
        if self.enabled and self.google_sheets is None:
            # Try to load from env if not provided
            self.google_sheets = GoogleSheetsConfig.from_env()
            if not self.google_sheets.is_configured:
                # If still not configured, disable portfolio manager
                self.enabled = False
        return self

    @property
    def is_configured(self) -> bool:
        """Check if portfolio manager is properly configured."""
        return self.enabled and self.google_sheets is not None and self.google_sheets.is_configured

    @classmethod
    def from_env(cls) -> "PortfolioManagerConfig":
        """Create portfolio manager config from environment variables."""
        enabled = os.getenv("PORTFOLIO_MANAGER_ENABLED", "false").lower() == "true"
        google_sheets = GoogleSheetsConfig.from_env()
        return cls(
            enabled=enabled and google_sheets.is_configured,
            google_sheets=google_sheets if google_sheets.is_configured else None,
            max_position_size=float(os.getenv("PORTFOLIO_MAX_POSITION_SIZE", "0.20")),
            min_cash_reserve=float(os.getenv("PORTFOLIO_MIN_CASH_RESERVE", "0.10")),
        )


class TradingAgentsConfig(BaseModel):
    """Root configuration model for TradingAgents."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    data_vendors: DataVendorConfig = Field(default_factory=DataVendorConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    debate: DebateConfig = Field(default_factory=DebateConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    portfolio_manager: PortfolioManagerConfig = Field(default_factory=PortfolioManagerConfig)

    @classmethod
    def from_legacy_dict(cls, config: Dict) -> "TradingAgentsConfig":
        """Create config from legacy dictionary format.

        Args:
            config: Legacy configuration dictionary (DEFAULT_CONFIG format)

        Returns:
            TradingAgentsConfig instance
        """
        llm = LLMConfig(
            provider=config.get("llm_provider", "openai"),
            deep_think_model=config.get("deep_think_llm", "o4-mini"),
            quick_think_model=config.get("quick_think_llm", "gpt-4o-mini"),
            backend_url=config.get("backend_url", "https://api.openai.com/v1"),
            api_key_env_var=config.get("api_key_env_var", "OPENAI_API_KEY"),
        )

        embedding = EmbeddingConfig(
            provider=config.get("embedding_provider", "same_as_llm"),
            model=config.get("embedding_model"),
            backend_url=config.get("embedding_backend_url"),
            api_key_env_var=config.get("embedding_api_key_env_var"),
            disabled=config.get("disable_embeddings", False),
        )

        data_vendors_dict = config.get("data_vendors", {})
        data_vendors = DataVendorConfig(
            core_stock_apis=data_vendors_dict.get("core_stock_apis", "yfinance"),
            technical_indicators=data_vendors_dict.get("technical_indicators", "yfinance"),
            fundamental_data=data_vendors_dict.get("fundamental_data", "yfinance"),
            news_data=data_vendors_dict.get("news_data", "alpha_vantage"),
            tool_overrides=config.get("tool_vendors", {}),
        )

        paths = PathConfig(
            project_dir=Path(config["project_dir"]) if "project_dir" in config else None,
            results_dir=Path(config["results_dir"]) if "results_dir" in config else None,
            data_dir=Path(config["data_dir"]) if config.get("data_dir") else None,
            data_cache_dir=Path(config["data_cache_dir"]) if "data_cache_dir" in config else None,
        )

        debate = DebateConfig(
            max_debate_rounds=config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=config.get("max_risk_discuss_rounds", 1),
            max_recur_limit=config.get("max_recur_limit", 100),
        )

        # Handle storage config from legacy dict
        storage_dict = config.get("storage", {})
        r2_dict = storage_dict.get("r2", {})
        r2_config = None
        if r2_dict:
            r2_config = R2StorageConfig(
                account_id=r2_dict.get("account_id"),
                access_key_id=r2_dict.get("access_key_id"),
                secret_access_key=r2_dict.get("secret_access_key"),
                bucket_name=r2_dict.get("bucket_name"),
                endpoint_url=r2_dict.get("endpoint_url"),
                presigned_url_expiry=r2_dict.get("presigned_url_expiry", 3600),
            )
            if not r2_config.is_configured:
                r2_config = None

        storage = StorageConfig(
            local_path=Path(storage_dict["local_path"]) if storage_dict.get("local_path") else None,
            r2=r2_config,
        )

        return cls(
            llm=llm,
            embedding=embedding,
            data_vendors=data_vendors,
            paths=paths,
            debate=debate,
            storage=storage,
        )

    def to_legacy_dict(self) -> Dict:
        """Convert to legacy dictionary format for backward compatibility.

        Returns:
            Dictionary in DEFAULT_CONFIG format
        """
        return {
            "project_dir": str(self.paths.project_dir),
            "results_dir": str(self.paths.results_dir),
            "data_dir": str(self.paths.data_dir) if self.paths.data_dir else None,
            "data_cache_dir": str(self.paths.data_cache_dir),
            "llm_provider": self.llm.provider,
            "deep_think_llm": self.llm.deep_think_model,
            "quick_think_llm": self.llm.quick_think_model,
            "backend_url": self.llm.backend_url,
            "api_key_env_var": self.llm.api_key_env_var,
            "embedding_model": self.embedding.model,
            "embedding_provider": self.embedding.provider,
            "embedding_backend_url": self.embedding.backend_url,
            "embedding_api_key_env_var": self.embedding.api_key_env_var,
            "disable_embeddings": self.embedding.disabled,
            "max_debate_rounds": self.debate.max_debate_rounds,
            "max_risk_discuss_rounds": self.debate.max_risk_discuss_rounds,
            "max_recur_limit": self.debate.max_recur_limit,
            "data_vendors": {
                "core_stock_apis": self.data_vendors.core_stock_apis,
                "technical_indicators": self.data_vendors.technical_indicators,
                "fundamental_data": self.data_vendors.fundamental_data,
                "news_data": self.data_vendors.news_data,
            },
            "tool_vendors": self.data_vendors.tool_overrides,
            "storage": {
                "local_path": str(self.storage.local_path) if self.storage.local_path else None,
                "r2": {
                    "account_id": self.storage.r2.account_id,
                    "access_key_id": self.storage.r2.access_key_id,
                    "secret_access_key": self.storage.r2.secret_access_key,
                    "bucket_name": self.storage.r2.bucket_name,
                    "endpoint_url": self.storage.r2.endpoint_url,
                    "presigned_url_expiry": self.storage.r2.presigned_url_expiry,
                } if self.storage.r2 else None,
            },
        }

    @classmethod
    def from_env(cls) -> "TradingAgentsConfig":
        """Create config from environment variables.

        Environment variables:
            LLM_PROVIDER, LLM_DEEP_THINK_MODEL, LLM_QUICK_THINK_MODEL,
            LLM_BACKEND_URL, LLM_API_KEY_ENV_VAR,
            EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_BACKEND_URL,
            TRADINGAGENTS_RESULTS_DIR, REPORTS_OUTPUT_DIR,
            R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
            R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_PRESIGNED_URL_EXPIRY, etc.

        Returns:
            TradingAgentsConfig instance
        """
        llm = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            deep_think_model=os.getenv("LLM_DEEP_THINK_MODEL", "o4-mini"),
            quick_think_model=os.getenv("LLM_QUICK_THINK_MODEL", "gpt-4o-mini"),
            backend_url=os.getenv("LLM_BACKEND_URL", "https://api.openai.com/v1"),
            api_key_env_var=os.getenv("LLM_API_KEY_ENV_VAR", "OPENAI_API_KEY"),
        )

        embedding_disabled = os.getenv("DISABLE_EMBEDDINGS", "false").lower() == "true"
        embedding = EmbeddingConfig(
            provider=os.getenv("EMBEDDING_PROVIDER", "same_as_llm"),
            model=os.getenv("EMBEDDING_MODEL"),
            backend_url=os.getenv("EMBEDDING_BACKEND_URL"),
            api_key_env_var=os.getenv("EMBEDDING_API_KEY_ENV_VAR"),
            disabled=embedding_disabled,
        )

        data_vendors = DataVendorConfig(
            core_stock_apis=os.getenv("VENDOR_CORE_STOCK", "yfinance"),
            technical_indicators=os.getenv("VENDOR_INDICATORS", "yfinance"),
            fundamental_data=os.getenv("VENDOR_FUNDAMENTALS", "yfinance"),
            news_data=os.getenv("VENDOR_NEWS", "alpha_vantage"),
        )

        paths = PathConfig(
            results_dir=Path(os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results")),
            data_dir=Path(os.getenv("TRADINGAGENTS_DATA_DIR")) if os.getenv("TRADINGAGENTS_DATA_DIR") else None,
        )

        debate = DebateConfig(
            max_debate_rounds=int(os.getenv("MAX_DEBATE_ROUNDS", "1")),
            max_risk_discuss_rounds=int(os.getenv("MAX_RISK_DISCUSS_ROUNDS", "1")),
            max_recur_limit=int(os.getenv("MAX_RECUR_LIMIT", "100")),
        )

        storage = StorageConfig.from_env()

        return cls(
            llm=llm,
            embedding=embedding,
            data_vendors=data_vendors,
            paths=paths,
            debate=debate,
            storage=storage,
        )
