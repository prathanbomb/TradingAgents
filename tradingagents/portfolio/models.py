"""Portfolio data models for tracking positions and transactions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal


@dataclass
class Position:
    """Represents a current holding in the portfolio."""

    ticker: str
    shares: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    portfolio_percentage: float

    def __post_init__(self):
        """Validate and normalize the position data."""
        self.ticker = self.ticker.upper().strip()
        if self.shares <= 0:
            raise ValueError(f"Shares must be positive for {self.ticker}")
        if self.avg_cost <= 0:
            raise ValueError(f"Average cost must be positive for {self.ticker}")
        if self.current_price <= 0:
            raise ValueError(f"Current price must be positive for {self.ticker}")

    @property
    def unrealized_pnl_percentage(self) -> float:
        """Calculate unrealized P&L as a percentage."""
        if self.avg_cost == 0:
            return 0.0
        return ((self.current_price - self.avg_cost) / self.avg_cost) * 100

    @property
    is_profitable(self) -> bool:
        """Check if position is profitable."""
        return self.unrealized_pnl > 0

    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percentage": self.unrealized_pnl_percentage,
            "portfolio_percentage": self.portfolio_percentage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """Create Position from dictionary."""
        return cls(
            ticker=data["ticker"],
            shares=data["shares"],
            avg_cost=data["avg_cost"],
            current_price=data["current_price"],
            market_value=data["market_value"],
            unrealized_pnl=data["unrealized_pnl"],
            portfolio_percentage=data["portfolio_percentage"],
        )


@dataclass
class Transaction:
    """Represents a buy or sell transaction in the portfolio."""

    date: str
    ticker: str
    type: str  # "buy" or "sell"
    shares: float
    price: float
    fees: float = 0.0
    total: Optional[float] = None

    def __post_init__(self):
        """Validate and normalize the transaction data."""
        self.ticker = self.ticker.upper().strip()
        self.type = self.type.lower().strip()
        if self.type not in ("buy", "sell"):
            raise ValueError(f"Transaction type must be 'buy' or 'sell', got '{self.type}'")
        if self.shares <= 0:
            raise ValueError(f"Shares must be positive for {self.ticker} {self.type}")
        if self.price <= 0:
            raise ValueError(f"Price must be positive for {self.ticker} {self.type}")
        if self.fees < 0:
            raise ValueError(f"Fees cannot be negative for {self.ticker} {self.type}")

        # Calculate total if not provided
        if self.total is None:
            if self.type == "buy":
                self.total = -(self.shares * self.price + self.fees)
            else:
                self.total = self.shares * self.price - self.fees

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy transaction."""
        return self.type == "buy"

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell transaction."""
        return self.type == "sell"

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "date": self.date,
            "ticker": self.ticker,
            "type": self.type,
            "shares": self.shares,
            "price": self.price,
            "fees": self.fees,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """Create Transaction from dictionary."""
        return cls(
            date=data["date"],
            ticker=data["ticker"],
            type=data["type"],
            shares=data["shares"],
            price=data["price"],
            fees=data.get("fees", 0.0),
            total=data.get("total"),
        )


@dataclass
class PortfolioSummary:
    """Summary of the entire portfolio state."""

    total_value: float
    cash_balance: float
    positions: List[Position] = field(default_factory=list)
    transactions: List[Transaction] = field(default_factory=list)
    daily_pnl: float = 0.0
    overall_pnl: float = 0.0
    last_updated: str = ""

    def __post_init__(self):
        """Validate and set default last_updated."""
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()
        if self.total_value < 0:
            raise ValueError("Total value cannot be negative")
        if self.cash_balance < 0:
            raise ValueError("Cash balance cannot be negative")

    @property
    def invested_value(self) -> float:
        """Calculate total value of all positions."""
        return sum(p.market_value for p in self.positions)

    @property
    def position_count(self) -> int:
        """Get the number of positions."""
        return len(self.positions)

    @property
    def transaction_count(self) -> int:
        """Get the number of transactions."""
        return len(self.transactions)

    @property
    def cash_percentage(self) -> float:
        """Calculate cash as percentage of total portfolio."""
        if self.total_value == 0:
            return 0.0
        return (self.cash_balance / self.total_value) * 100

    def get_position(self, ticker: str) -> Optional[Position]:
        """Get a position by ticker symbol."""
        ticker = ticker.upper().strip()
        for pos in self.positions:
            if pos.ticker == ticker:
                return pos
        return None

    def has_position(self, ticker: str) -> bool:
        """Check if portfolio has a position in the given ticker."""
        return self.get_position(ticker) is not None

    def get_position_percentage(self, ticker: str) -> float:
        """Get the percentage of portfolio allocated to a ticker."""
        position = self.get_position(ticker)
        if position:
            return position.portfolio_percentage
        return 0.0

    def to_dict(self) -> dict:
        """Convert summary to dictionary."""
        return {
            "total_value": self.total_value,
            "cash_balance": self.cash_balance,
            "invested_value": self.invested_value,
            "cash_percentage": self.cash_percentage,
            "position_count": self.position_count,
            "transaction_count": self.transaction_count,
            "daily_pnl": self.daily_pnl,
            "overall_pnl": self.overall_pnl,
            "last_updated": self.last_updated,
            "positions": [p.to_dict() for p in self.positions],
            "transactions": [t.to_dict() for t in self.transactions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortfolioSummary":
        """Create PortfolioSummary from dictionary."""
        return cls(
            total_value=data["total_value"],
            cash_balance=data["cash_balance"],
            positions=[Position.from_dict(p) for p in data.get("positions", [])],
            transactions=[Transaction.from_dict(t) for t in data.get("transactions", [])],
            daily_pnl=data.get("daily_pnl", 0.0),
            overall_pnl=data.get("overall_pnl", 0.0),
            last_updated=data.get("last_updated", ""),
        )

    def format_summary(self) -> str:
        """Format portfolio summary for display in agent prompts."""
        lines = [
            f"Total Portfolio Value: ${self.total_value:,.2f}",
            f"Cash Balance: ${self.cash_balance:,.2f} ({self.cash_percentage:.1f}%)",
            f"Invested: ${self.invested_value:,.2f}",
            f"Number of Positions: {self.position_count}",
        ]

        if self.overall_pnl != 0:
            pnl_sign = "+" if self.overall_pnl > 0 else ""
            lines.append(f"Overall P&L: {pnl_sign}${self.overall_pnl:,.2f}")

        if self.positions:
            lines.append("\nCurrent Positions:")
            for pos in sorted(self.positions, key=lambda p: p.market_value, reverse=True):
                pnl_sign = "+" if pos.unrealized_pnl > 0 else ""
                lines.append(
                    f"  - {pos.ticker}: {pos.shares} shares @ ${pos.avg_cost:.2f} | "
                    f"Current: ${pos.current_price:.2f} | "
                    f"Value: ${pos.market_value:,.2f} ({pos.portfolio_percentage:.1f}%) | "
                    f"P&L: {pnl_sign}${pos.unrealized_pnl:,.2f} ({pos.unrealized_pnl_percentage:+.1f}%)"
                )

        return "\n".join(lines)
