"""
Paper Trading Account for the Crypto Paper Trading System.

This module manages the simulated trading account:
- Cash balance tracking (USDT)
- Position management
- Unrealized PnL calculation
- Trading fee simulation
- Balance validation

IMPORTANT: This is FAKE MONEY only. No real funds are involved.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

import config
import database


class PaperAccount:
    """
    Paper trading account manager.
    
    This class simulates a real trading account with:
    - Starting balance of 10,000 USDT (configurable)
    - Realistic trading fees (0.1% per trade)
    - Position tracking with average entry price
    - Realized and unrealized PnL calculation
    
    All data is persisted to SQLite for durability.
    """
    
    def __init__(self, starting_balance: float = None):
        """
        Initialize the paper trading account.
        
        Args:
            starting_balance: Initial USDT balance (default from config)
        """
        self.starting_balance = starting_balance or config.STARTING_BALANCE_USDT
        self.fee_percent = config.TRADING_FEE_PERCENT / 100  # Convert to decimal
        
        # Initialize database and account
        database.initialize_database()
        database.initialize_account(self.starting_balance)
        
        print(f"[ACCOUNT] Paper trading account ready")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print current account summary."""
        account = self.get_account_info()
        print(f"[ACCOUNT] Cash: ${account['cash_balance']:,.2f} USDT")
        print(f"[ACCOUNT] Equity: ${account['total_equity']:,.2f} USDT")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get current account information.
        
        Returns:
            Dict with cash_balance, total_equity, positions, etc.
        """
        account = database.get_account()
        
        if account is None:
            # Should not happen after initialization, but handle gracefully
            database.initialize_account(self.starting_balance)
            account = database.get_account()
        
        positions = database.get_all_positions()
        
        return {
            'cash_balance': account['cash_balance'],
            'total_equity': account['total_equity'],
            'positions': positions,
            'last_updated': account['last_updated']
        }
    
    def get_cash_balance(self) -> float:
        """
        Get current available cash balance (USDT).
        
        Returns:
            Available cash in USDT
        """
        account = database.get_account()
        return account['cash_balance'] if account else 0.0
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
        
        Returns:
            Position dict or None if no position
        """
        return database.get_position(symbol)
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of position dicts
        """
        return database.get_all_positions()
    
    def calculate_fee(self, amount_usdt: float) -> float:
        """
        Calculate trading fee for a given trade amount.
        
        Args:
            amount_usdt: Trade value in USDT
        
        Returns:
            Fee amount in USDT
        """
        return amount_usdt * self.fee_percent
    
    def can_afford(self, amount_usdt: float) -> bool:
        """
        Check if account can afford a trade (including fees).
        
        Args:
            amount_usdt: Trade amount in USDT
        
        Returns:
            True if balance is sufficient
        """
        fee = self.calculate_fee(amount_usdt)
        total_cost = amount_usdt + fee
        cash = self.get_cash_balance()
        
        return cash >= total_cost
    
    def update_cash_balance(self, new_balance: float) -> None:
        """
        Update the cash balance.
        
        Args:
            new_balance: New cash balance in USDT
        """
        # Recalculate total equity
        total_equity = self.calculate_total_equity(new_balance)
        database.update_account(new_balance, total_equity)
    
    def calculate_total_equity(self, cash_balance: float = None) -> float:
        """
        Calculate total portfolio equity (cash + positions value).
        
        Args:
            cash_balance: Override cash balance (optional)
        
        Returns:
            Total equity in USDT
        """
        if cash_balance is None:
            cash_balance = self.get_cash_balance()
        
        positions_value = 0.0
        
        for position in self.get_all_positions():
            # Get current price for the position
            current_price = database.get_latest_price(position['symbol'])
            
            if current_price:
                positions_value += position['amount'] * current_price
            else:
                # Use entry price if current price not available
                positions_value += position['amount'] * position['avg_entry_price']
        
        return cash_balance + positions_value
    
    def update_position(self, symbol: str, amount: float, 
                        avg_entry_price: float) -> None:
        """
        Update a position.
        
        Args:
            symbol: Trading pair
            amount: New position size (0 to close)
            avg_entry_price: Average entry price
        """
        database.update_position(symbol, amount, avg_entry_price)
        
        # Recalculate and update total equity
        cash = self.get_cash_balance()
        total_equity = self.calculate_total_equity(cash)
        database.update_account(cash, total_equity)
    
    def calculate_unrealized_pnl(self, symbol: str, 
                                  current_price: float) -> float:
        """
        Calculate unrealized PnL for a position.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
        
        Returns:
            Unrealized PnL in USDT
        """
        position = self.get_position(symbol)
        
        if position is None:
            return 0.0
        
        entry_value = position['amount'] * position['avg_entry_price']
        current_value = position['amount'] * current_price
        
        return current_value - entry_value
    
    def calculate_total_unrealized_pnl(self) -> float:
        """
        Calculate total unrealized PnL across all positions.
        
        Returns:
            Total unrealized PnL in USDT
        """
        total_pnl = 0.0
        
        for position in self.get_all_positions():
            current_price = database.get_latest_price(position['symbol'])
            
            if current_price:
                pnl = self.calculate_unrealized_pnl(position['symbol'], current_price)
                total_pnl += pnl
        
        return total_pnl
    
    def record_equity_snapshot(self) -> float:
        """
        Record current equity for performance tracking.
        
        Returns:
            Current total equity
        """
        equity = self.calculate_total_equity()
        database.record_equity(equity)
        return equity
    
    def get_trade_history(self, symbol: str = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get trade history.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum trades to return
        
        Returns:
            List of trade dicts
        """
        return database.get_trades(symbol, limit)
    
    def reset_account(self) -> None:
        """
        Reset the account to starting balance.
        
        WARNING: This clears all trades, positions, and history!
        """
        print("[ACCOUNT] Resetting account...")
        database.reset_database()
        database.initialize_account(self.starting_balance)
        print(f"[ACCOUNT] Reset complete. Balance: ${self.starting_balance:,.2f} USDT")
    
    def print_status(self) -> None:
        """Print detailed account status."""
        account = self.get_account_info()
        
        print("\n" + "="*50)
        print("PAPER TRADING ACCOUNT STATUS")
        print("="*50)
        print(f"Cash Balance:    ${account['cash_balance']:>12,.2f} USDT")
        print(f"Total Equity:    ${account['total_equity']:>12,.2f} USDT")
        
        # Calculate return
        pnl = account['total_equity'] - self.starting_balance
        pnl_percent = (pnl / self.starting_balance) * 100
        sign = "+" if pnl >= 0 else ""
        print(f"Total PnL:       ${pnl:>12,.2f} USDT ({sign}{pnl_percent:.2f}%)")
        
        # Print positions
        positions = account['positions']
        if positions:
            print("\nOpen Positions:")
            print("-"*50)
            for pos in positions:
                current_price = database.get_latest_price(pos['symbol'])
                if current_price:
                    unrealized_pnl = self.calculate_unrealized_pnl(
                        pos['symbol'], current_price
                    )
                    pnl_str = f"${unrealized_pnl:+,.2f}"
                else:
                    current_price = pos['avg_entry_price']
                    pnl_str = "N/A"
                
                print(f"  {pos['symbol']}")
                print(f"    Amount: {pos['amount']:.6f}")
                print(f"    Entry:  ${pos['avg_entry_price']:,.2f}")
                print(f"    Current: ${current_price:,.2f}")
                print(f"    PnL:    {pnl_str}")
        else:
            print("\nNo open positions")
        
        print("="*50 + "\n")


def get_paper_account() -> PaperAccount:
    """
    Factory function to create a PaperAccount instance.
    
    Returns:
        Configured PaperAccount instance
    """
    return PaperAccount()


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    # Create account
    account = PaperAccount()
    
    # Print initial status
    account.print_status()
    
    # Check if we can afford a trade
    print(f"Can afford $5000 trade: {account.can_afford(5000)}")
    print(f"Can afford $15000 trade: {account.can_afford(15000)}")
    
    # Calculate fee
    fee = account.calculate_fee(1000)
    print(f"Fee for $1000 trade: ${fee:.2f}")
