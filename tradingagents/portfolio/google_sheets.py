"""Google Sheets integration for portfolio management.

This module provides a service for reading and writing portfolio data
to Google Sheets, allowing for easy portfolio tracking and management.
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from tradingagents.portfolio.models import Position, Transaction, PortfolioSummary

logger = logging.getLogger(__name__)


class GoogleSheetsPortfolio:
    """Service for managing portfolio data in Google Sheets."""

    # Sheet names
    SHEET_POSITIONS = "Positions"
    SHEET_TRANSACTIONS = "Transactions"
    SHEET_SUMMARY = "Summary"

    def __init__(
        self,
        sheet_id: str,
        credentials_path: str,
        sheet_name: str = "Trading Portfolio",
    ):
        """Initialize the Google Sheets portfolio service.

        Args:
            sheet_id: The Google Sheet ID
            credentials_path: Path to Google credentials JSON file
            sheet_name: Name of the spreadsheet (for logging)
        """
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.credentials_path = credentials_path

        # Lazy load the sheets API
        self._service = None
        self._spreadsheet_id = None

    @property
    def service(self):
        """Get or create the Google Sheets service."""
        if self._service is None:
            self._service = self._create_service()
        return self._service

    def _create_service(self):
        """Create the Google Sheets API service."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            # Check if credentials file exists
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    f"Google Sheets credentials file not found: {self.credentials_path}\n"
                    "Please download credentials from Google Cloud Console and save to this path."
                )

            # Load credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )

            # Build the service
            service = build("sheets", "v4", credentials=credentials)
            logger.info(f"Connected to Google Sheets: {self.sheet_name}")
            return service

        except ImportError as e:
            raise ImportError(
                "Google Sheets dependencies not installed. "
                "Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            ) from e

    def _get_sheet_data(self, range_name: str) -> List[List[str]]:
        """Get data from a sheet range.

        Args:
            range_name: The range to read (e.g., "Positions!A1:G100")

        Returns:
            List of rows (each row is a list of values)
        """
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.sheet_id, range=range_name)
                .execute()
            )
            return result.get("values", [])
        except Exception as e:
            logger.error(f"Error reading sheet {range_name}: {e}")
            raise

    def _update_sheet_data(
        self, range_name: str, values: List[List[str]]
    ) -> Dict[str, Any]:
        """Update data in a sheet range.

        Args:
            range_name: The range to update
            values: The values to write

        Returns:
            API response
        """
        try:
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )
            return result
        except Exception as e:
            logger.error(f"Error writing to sheet {range_name}: {e}")
            raise

    def _ensure_sheets_exist(self):
        """Ensure all required sheets exist in the spreadsheet."""
        try:
            # Get spreadsheet metadata
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.sheet_id)
                .execute()
            )

            existing_sheets = [
                sheet["properties"]["title"]
                for sheet in spreadsheet.get("sheets", [])
            ]

            # Check which sheets are missing
            required_sheets = [
                self.SHEET_POSITIONS,
                self.SHEET_TRANSACTIONS,
                self.SHEET_SUMMARY,
            ]
            missing_sheets = [
                s for s in required_sheets if s not in existing_sheets
            ]

            if missing_sheets:
                logger.info(f"Creating missing sheets: {missing_sheets}")
                # Create missing sheets
                requests = [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name,
                                "gridProperties": {"rowCount": 1000, "columnCount": 20},
                            }
                        }
                    }
                    for sheet_name in missing_sheets
                ]

                if requests:
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.sheet_id, body={"requests": requests}
                    ).execute()

        except Exception as e:
            logger.warning(f"Could not verify sheets exist: {e}")

    def initialize_sheets(self) -> None:
        """Initialize the spreadsheet with headers if needed."""
        self._ensure_sheets_exist()

        # Initialize Positions sheet
        positions_data = self._get_sheet_data(f"{self.SHEET_POSITIONS}!A1:G1")
        if not positions_data:
            headers = [
                ["Ticker", "Shares", "Avg Cost", "Current Price", "Market Value", "Unrealized P&L", "% of Portfolio"]
            ]
            self._update_sheet_data(f"{self.SHEET_POSITIONS}!A1:G1", headers)
            logger.info(f"Initialized {self.SHEET_POSITIONS} sheet")

        # Initialize Transactions sheet
        transactions_data = self._get_sheet_data(f"{self.SHEET_TRANSACTIONS}!A1:H1")
        if not transactions_data:
            headers = [
                ["Date", "Ticker", "Type", "Shares", "Price", "Fees", "Total", "Notes"]
            ]
            self._update_sheet_data(f"{self.SHEET_TRANSACTIONS}!A1:H1", headers)
            logger.info(f"Initialized {self.SHEET_TRANSACTIONS} sheet")

        # Initialize Summary sheet
        summary_data = self._get_sheet_data(f"{self.SHEET_SUMMARY}!A1:B10")
        if not summary_data or len(summary_data) < 5:
            # Will be updated when portfolio is loaded/saved
            logger.info(f"Initialized {self.SHEET_SUMMARY} sheet")

    def get_portfolio(self) -> PortfolioSummary:
        """Load the complete portfolio from Google Sheets.

        Returns:
            PortfolioSummary object with current state
        """
        try:
            # Load positions
            positions = self._load_positions()

            # Load transactions
            transactions = self._load_transactions()

            # Load summary
            summary_data = self._load_summary()

            return PortfolioSummary(
                total_value=summary_data.get("total_value", 0.0),
                cash_balance=summary_data.get("cash_balance", 0.0),
                positions=positions,
                transactions=transactions,
                daily_pnl=summary_data.get("daily_pnl", 0.0),
                overall_pnl=summary_data.get("overall_pnl", 0.0),
                last_updated=summary_data.get("last_updated", ""),
            )

        except Exception as e:
            logger.error(f"Error loading portfolio: {e}")
            # Return empty portfolio on error
            return PortfolioSummary(
                total_value=0.0,
                cash_balance=0.0,
                positions=[],
                transactions=[],
            )

    def _load_positions(self) -> List[Position]:
        """Load positions from the Positions sheet."""
        rows = self._get_sheet_data(f"{self.SHEET_POSITIONS}!A2:G1000")
        positions = []

        for row in rows:
            if len(row) < 7:
                continue
            try:
                position = Position(
                    ticker=row[0],
                    shares=float(row[1]),
                    avg_cost=float(row[2]),
                    current_price=float(row[3]),
                    market_value=float(row[4]),
                    unrealized_pnl=float(row[5]),
                    portfolio_percentage=float(row[6]),
                )
                positions.append(position)
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping invalid position row {row}: {e}")

        return positions

    def _load_transactions(self) -> List[Transaction]:
        """Load transactions from the Transactions sheet."""
        rows = self._get_sheet_data(f"{self.SHEET_TRANSACTIONS}!A2:H1000")
        transactions = []

        for row in rows:
            if len(row) < 7:
                continue
            try:
                transaction = Transaction(
                    date=row[0],
                    ticker=row[1],
                    type=row[2],
                    shares=float(row[3]),
                    price=float(row[4]),
                    fees=float(row[5]) if len(row) > 5 and row[5] else 0.0,
                    total=float(row[6]) if len(row) > 6 and row[6] else None,
                )
                transactions.append(transaction)
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping invalid transaction row {row}: {e}")

        # Sort by date descending (newest first)
        transactions.sort(key=lambda t: t.date, reverse=True)
        return transactions

    def _load_summary(self) -> Dict[str, Any]:
        """Load summary data from the Summary sheet."""
        rows = self._get_sheet_data(f"{self.SHEET_SUMMARY}!A1:B20")
        summary = {}

        for row in rows:
            if len(row) < 2:
                continue
            key = row[0].strip().lower().replace(" ", "_")
            value = row[1]

            # Parse numeric values
            try:
                if key in ["total_value", "cash_balance", "daily_pnl", "overall_pnl"]:
                    summary[key] = float(value)
                else:
                    summary[key] = value
            except (ValueError, TypeError):
                summary[key] = value

        return summary

    def save_portfolio(self, portfolio: PortfolioSummary) -> None:
        """Save the complete portfolio to Google Sheets.

        Args:
            portfolio: PortfolioSummary object to save
        """
        try:
            # Save positions
            self._save_positions(portfolio.positions)

            # Save transactions
            self._save_transactions(portfolio.transactions)

            # Save summary
            self._save_summary(portfolio)

            logger.info(f"Portfolio saved to Google Sheets")

        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            raise

    def _save_positions(self, positions: List[Position]) -> None:
        """Save positions to the Positions sheet."""
        # Prepare data rows
        rows = [["Ticker", "Shares", "Avg Cost", "Current Price", "Market Value", "Unrealized P&L", "% of Portfolio"]]

        for pos in sorted(positions, key=lambda p: p.market_value, reverse=True):
            rows.append([
                pos.ticker,
                str(pos.shares),
                str(pos.avg_cost),
                str(pos.current_price),
                str(pos.market_value),
                str(pos.unrealized_pnl),
                str(pos.portfolio_percentage),
            ])

        # Clear and update
        range_name = f"{self.SHEET_POSITIONS}!A1:G{len(rows)}"
        self._update_sheet_data(range_name, rows)

    def _save_transactions(self, transactions: List[Transaction]) -> None:
        """Save transactions to the Transactions sheet."""
        # Keep header
        rows = [["Date", "Ticker", "Type", "Shares", "Price", "Fees", "Total", "Notes"]]

        # Sort by date descending (newest first)
        for txn in sorted(transactions, key=lambda t: t.date, reverse=True):
            rows.append([
                txn.date,
                txn.ticker,
                txn.type,
                str(txn.shares),
                str(txn.price),
                str(txn.fees),
                str(txn.total if txn.total is not None else ""),
                "",  # Notes column
            ])

        # Clear and update
        range_name = f"{self.SHEET_TRANSACTIONS}!A1:H{len(rows)}"
        self._update_sheet_data(range_name, rows)

    def _save_summary(self, portfolio: PortfolioSummary) -> None:
        """Save summary to the Summary sheet."""
        now = datetime.now().isoformat()

        rows = [
            ["Total Value", str(portfolio.total_value)],
            ["Cash Balance", str(portfolio.cash_balance)],
            ["Invested Value", str(portfolio.invested_value)],
            ["Cash Percentage", f"{portfolio.cash_percentage:.1f}%"],
            ["Number of Positions", str(portfolio.position_count)],
            ["Daily P&L", str(portfolio.daily_pnl)],
            ["Overall P&L", str(portfolio.overall_pnl)],
            ["Last Updated", now],
        ]

        range_name = f"{self.SHEET_SUMMARY}!A1:B{len(rows)}"
        self._update_sheet_data(range_name, rows)

    def add_transaction(self, transaction: Transaction) -> None:
        """Add a new transaction to the portfolio.

        Args:
            transaction: Transaction to add
        """
        portfolio = self.get_portfolio()
        portfolio.transactions.append(transaction)
        self.save_portfolio(portfolio)
        logger.info(f"Added transaction: {transaction.type} {transaction.shares} {transaction.ticker}")

    def update_position(
        self,
        ticker: str,
        shares: Optional[float] = None,
        avg_cost: Optional[float] = None,
        current_price: Optional[float] = None,
    ) -> None:
        """Update or add a position in the portfolio.

        Args:
            ticker: Ticker symbol
            shares: Number of shares (optional)
            avg_cost: Average cost (optional)
            current_price: Current market price (optional)
        """
        portfolio = self.get_portfolio()

        # Find existing position or create new one
        position = portfolio.get_position(ticker)

        if position:
            # Update existing
            if shares is not None:
                position.shares = shares
            if avg_cost is not None:
                position.avg_cost = avg_cost
            if current_price is not None:
                position.current_price = current_price
                position.market_value = position.shares * current_price
                position.unrealized_pnl = (current_price - position.avg_cost) * position.shares
        else:
            # Create new position
            if shares is None or avg_cost is None or current_price is None:
                raise ValueError("shares, avg_cost, and current_price required for new position")

            market_value = shares * current_price
            unrealized_pnl = (current_price - avg_cost) * shares
            portfolio_percentage = (market_value / portfolio.total_value * 100) if portfolio.total_value > 0 else 0

            position = Position(
                ticker=ticker,
                shares=shares,
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                portfolio_percentage=portfolio_percentage,
            )
            portfolio.positions.append(position)

        self.save_portfolio(portfolio)
        logger.info(f"Updated position: {ticker}")
