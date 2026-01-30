"""
Trade Executor for the Crypto Paper Trading System.

This module handles simulated trade execution:
- Market buy orders
- Market sell orders
- Trade logging
- PnL tracking (realized and unrealized)
- Balance validation

IMPORTANT: All trades are SIMULATED. No real orders are placed.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import config
import database
from account import PaperAccount


class TradeExecutor:
    """
    Simulated trade executor for paper trading.
    
    This class executes simulated market orders:
    - market_buy(symbol, amount_usdt): Buy crypto with USDT
    - market_sell(symbol, amount_crypto): Sell crypto for USDT
    
    Features:
    - Realistic trading fees (0.1%)
    - Position averaging on buys
    - Realized PnL calculation on sells
    - Balance validation (rejects if insufficient funds)
    - Complete trade logging
    """
    
    def __init__(self, account: PaperAccount = None):
        """
        Initialize the trade executor.
        
        Args:
            account: PaperAccount instance (creates new if not provided)
        """
        self.account = account or PaperAccount()
        print("[EXECUTOR] Trade executor ready")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
        
        Returns:
            Current price or None if unavailable
        """
        return database.get_latest_price(symbol)
    
    def market_buy(self, symbol: str, amount_usdt: float) -> Dict[str, Any]:
        """
        Execute a simulated market buy order.
        
        This function:
        1. Validates sufficient balance
        2. Gets current market price
        3. Calculates trade size and fees
        4. Updates position (with averaging)
        5. Deducts from cash balance
        6. Logs the trade
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            amount_usdt: Amount in USDT to spend
        
        Returns:
            Dict with trade result:
            {
                'success': bool,
                'symbol': str,
                'side': 'buy',
                'amount': float (crypto amount),
                'price': float,
                'cost': float (USDT spent),
                'fee': float,
                'error': str (if failed)
            }
        """
        timestamp = datetime.now()
        
        # Validate minimum trade size
        if amount_usdt <= 0:
            return {
                'success': False,
                'error': 'Trade amount must be positive',
                'symbol': symbol,
                'side': 'buy'
            }
        
        # Get current price
        price = self.get_current_price(symbol)
        if price is None:
            return {
                'success': False,
                'error': f'No price data available for {symbol}',
                'symbol': symbol,
                'side': 'buy'
            }
        
        # Calculate fee and total cost
        fee = self.account.calculate_fee(amount_usdt)
        total_cost = amount_usdt + fee
        
        # Validate balance
        if not self.account.can_afford(amount_usdt):
            cash = self.account.get_cash_balance()
            return {
                'success': False,
                'error': f'Insufficient balance. Have ${cash:,.2f}, need ${total_cost:,.2f}',
                'symbol': symbol,
                'side': 'buy'
            }
        
        # Calculate crypto amount (after fee)
        crypto_amount = amount_usdt / price
        
        # Get existing position for averaging
        existing_position = self.account.get_position(symbol)
        
        if existing_position:
            # Calculate new average entry price
            old_amount = existing_position['amount']
            old_avg_price = existing_position['avg_entry_price']
            old_cost = old_amount * old_avg_price
            
            new_amount = old_amount + crypto_amount
            new_avg_price = (old_cost + amount_usdt) / new_amount
            
            self.account.update_position(symbol, new_amount, new_avg_price)
        else:
            # New position
            self.account.update_position(symbol, crypto_amount, price)
        
        # Deduct from cash balance
        new_cash = self.account.get_cash_balance() - total_cost
        self.account.update_cash_balance(new_cash)
        
        # Log the trade
        trade_id = database.log_trade(
            symbol=symbol,
            side='buy',
            amount=crypto_amount,
            price=price,
            fee=fee,
            pnl=0  # Buys don't have realized PnL
        )
        
        # Print trade confirmation
        print(f"[TRADE] BUY {symbol}")
        print(f"        Amount: {crypto_amount:.6f} @ ${price:,.2f}")
        print(f"        Cost: ${amount_usdt:,.2f} + ${fee:.2f} fee")
        
        return {
            'success': True,
            'trade_id': trade_id,
            'symbol': symbol,
            'side': 'buy',
            'amount': crypto_amount,
            'price': price,
            'cost': amount_usdt,
            'fee': fee,
            'total_cost': total_cost,
            'timestamp': timestamp.isoformat()
        }
    
    def market_sell(self, symbol: str, amount_crypto: float) -> Dict[str, Any]:
        """
        Execute a simulated market sell order.
        
        This function:
        1. Validates position exists and has sufficient amount
        2. Gets current market price
        3. Calculates proceeds and fees
        4. Calculates realized PnL
        5. Updates/closes position
        6. Adds to cash balance
        7. Logs the trade
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            amount_crypto: Amount of crypto to sell
        
        Returns:
            Dict with trade result:
            {
                'success': bool,
                'symbol': str,
                'side': 'sell',
                'amount': float (crypto amount),
                'price': float,
                'proceeds': float (USDT received),
                'fee': float,
                'pnl': float (realized PnL),
                'error': str (if failed)
            }
        """
        timestamp = datetime.now()
        
        # Validate minimum trade size
        if amount_crypto <= 0:
            return {
                'success': False,
                'error': 'Sell amount must be positive',
                'symbol': symbol,
                'side': 'sell'
            }
        
        # Get existing position
        position = self.account.get_position(symbol)
        
        if position is None:
            return {
                'success': False,
                'error': f'No position in {symbol}',
                'symbol': symbol,
                'side': 'sell'
            }
        
        if position['amount'] < amount_crypto:
            return {
                'success': False,
                'error': f'Insufficient {symbol}. Have {position["amount"]:.6f}, want to sell {amount_crypto:.6f}',
                'symbol': symbol,
                'side': 'sell'
            }
        
        # Get current price
        price = self.get_current_price(symbol)
        if price is None:
            return {
                'success': False,
                'error': f'No price data available for {symbol}',
                'symbol': symbol,
                'side': 'sell'
            }
        
        # Calculate gross proceeds
        gross_proceeds = amount_crypto * price
        
        # Calculate fee
        fee = self.account.calculate_fee(gross_proceeds)
        
        # Net proceeds after fee
        net_proceeds = gross_proceeds - fee
        
        # Calculate realized PnL
        entry_cost = amount_crypto * position['avg_entry_price']
        realized_pnl = net_proceeds - entry_cost
        
        # Update position
        new_amount = position['amount'] - amount_crypto
        
        if new_amount <= 0.000001:  # Close position (tiny amounts)
            self.account.update_position(symbol, 0, 0)
        else:
            # Keep same average entry price for remaining
            self.account.update_position(symbol, new_amount, position['avg_entry_price'])
        
        # Add to cash balance
        new_cash = self.account.get_cash_balance() + net_proceeds
        self.account.update_cash_balance(new_cash)
        
        # Log the trade
        trade_id = database.log_trade(
            symbol=symbol,
            side='sell',
            amount=amount_crypto,
            price=price,
            fee=fee,
            pnl=realized_pnl
        )
        
        # Print trade confirmation
        pnl_sign = "+" if realized_pnl >= 0 else ""
        print(f"[TRADE] SELL {symbol}")
        print(f"        Amount: {amount_crypto:.6f} @ ${price:,.2f}")
        print(f"        Proceeds: ${gross_proceeds:,.2f} - ${fee:.2f} fee = ${net_proceeds:,.2f}")
        print(f"        Realized PnL: {pnl_sign}${realized_pnl:,.2f}")
        
        return {
            'success': True,
            'trade_id': trade_id,
            'symbol': symbol,
            'side': 'sell',
            'amount': amount_crypto,
            'price': price,
            'gross_proceeds': gross_proceeds,
            'fee': fee,
            'net_proceeds': net_proceeds,
            'pnl': realized_pnl,
            'timestamp': timestamp.isoformat()
        }
    
    def sell_all(self, symbol: str) -> Dict[str, Any]:
        """
        Sell entire position in a symbol.
        
        Args:
            symbol: Trading pair to sell
        
        Returns:
            Trade result dict
        """
        position = self.account.get_position(symbol)
        
        if position is None:
            return {
                'success': False,
                'error': f'No position in {symbol}',
                'symbol': symbol,
                'side': 'sell'
            }
        
        return self.market_sell(symbol, position['amount'])
    
    def get_position_value(self, symbol: str) -> Tuple[float, float]:
        """
        Get current value and PnL of a position.
        
        Args:
            symbol: Trading pair
        
        Returns:
            Tuple of (current_value, unrealized_pnl)
        """
        position = self.account.get_position(symbol)
        
        if position is None:
            return (0.0, 0.0)
        
        price = self.get_current_price(symbol)
        if price is None:
            price = position['avg_entry_price']
        
        current_value = position['amount'] * price
        entry_value = position['amount'] * position['avg_entry_price']
        unrealized_pnl = current_value - entry_value
        
        return (current_value, unrealized_pnl)
    
    def get_total_realized_pnl(self) -> float:
        """
        Calculate total realized PnL from all trades.
        
        Returns:
            Total realized PnL in USDT
        """
        trades = database.get_trades(limit=10000)
        return sum(trade['pnl'] for trade in trades)
    
    def print_trade_summary(self) -> None:
        """Print summary of recent trades."""
        trades = database.get_trades(limit=10)
        
        print("\n" + "="*60)
        print("RECENT TRADES")
        print("="*60)
        
        if not trades:
            print("No trades yet")
        else:
            for trade in trades:
                dt = datetime.fromtimestamp(trade['timestamp'] / 1000)
                side_color = "BUY " if trade['side'] == 'buy' else "SELL"
                pnl_str = f"PnL: ${trade['pnl']:+,.2f}" if trade['pnl'] != 0 else ""
                
                print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] {side_color} {trade['symbol']}")
                print(f"    {trade['amount']:.6f} @ ${trade['price']:,.2f} (fee: ${trade['fee']:.2f}) {pnl_str}")
        
        print("="*60)
        print(f"Total Realized PnL: ${self.get_total_realized_pnl():,.2f}")
        print("="*60 + "\n")


def get_trade_executor(account: PaperAccount = None) -> TradeExecutor:
    """
    Factory function to create a TradeExecutor instance.
    
    Args:
        account: Optional PaperAccount to use
    
    Returns:
        Configured TradeExecutor instance
    """
    return TradeExecutor(account)


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    from market_tracker import MarketTracker
    
    # Initialize database
    database.initialize_database()
    
    # Create tracker and fetch some data
    tracker = MarketTracker(["BTC/USDT"])
    tracker.fetch_and_cache("BTC/USDT")
    
    # Create executor
    executor = TradeExecutor()
    
    # Print initial status
    executor.account.print_status()
    
    # Try a buy
    print("\n--- Executing buy order ---")
    result = executor.market_buy("BTC/USDT", 1000)
    print(f"Result: {result}")
    
    # Print status after buy
    executor.account.print_status()
    
    # Try a sell (half position)
    position = executor.account.get_position("BTC/USDT")
    if position:
        print("\n--- Executing sell order (half position) ---")
        result = executor.market_sell("BTC/USDT", position['amount'] / 2)
        print(f"Result: {result}")
    
    # Print final status
    executor.account.print_status()
    executor.print_trade_summary()
