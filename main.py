"""
Main Trading Loop for the Crypto Paper Trading System.

This is the entry point for the paper trading bot. It orchestrates:
1. Market data fetching
2. Indicator calculation
3. Strategy signal generation
4. Trade execution
5. Performance tracking

IMPORTANT: This is a PAPER TRADING system only.
- All money is FAKE
- No real orders are placed
- No wallets or private keys are used
- Only PUBLIC market data is accessed

Usage:
    python main.py

Press Ctrl+C to stop the trading loop.
"""

import sys
import time
import signal
from datetime import datetime
from typing import Optional

import config
import database
from market_tracker import MarketTracker
from indicators import calculate_all_indicators, get_latest_indicators
from account import PaperAccount
from executor import TradeExecutor
from strategies import RsiEmaStrategy, Signal
from analytics import PerformanceAnalytics


class PaperTradingBot:
    """
    Main paper trading bot that orchestrates all components.
    
    This class ties together:
    - MarketTracker: Fetches real-time market data
    - Indicators: Calculates technical indicators
    - Strategy: Generates trading signals
    - Executor: Executes simulated trades
    - Analytics: Tracks performance
    
    The bot runs a continuous loop that:
    1. Fetches latest market data
    2. Calculates indicators
    3. Asks the strategy for a signal
    4. Executes trades based on signals
    5. Records equity snapshots
    6. Repeats every N seconds
    """
    
    def __init__(self, 
                 symbol: str = None,
                 trade_amount: float = 500.0):
        """
        Initialize the paper trading bot.
        
        Args:
            symbol: Trading pair to trade (default from config)
            trade_amount: Amount in USDT per trade (default $500)
        """
        self.symbol = symbol or config.DEFAULT_SYMBOL
        self.trade_amount = trade_amount
        self.running = False
        self.iteration = 0
        
        # Initialize components
        print("=" * 60)
        print("CRYPTO PAPER TRADING BOT")
        print("=" * 60)
        print("\n*** PAPER TRADING ONLY - NO REAL MONEY ***\n")
        
        # Database
        database.initialize_database()
        
        # Market tracker
        self.tracker = MarketTracker([self.symbol])
        
        # Account and executor
        self.account = PaperAccount()
        self.executor = TradeExecutor(self.account)
        
        # Strategy
        self.strategy = RsiEmaStrategy()
        print(f"[STRATEGY] Using: {self.strategy.name}")
        
        # Analytics
        self.analytics = PerformanceAnalytics()
        
        print(f"[BOT] Trading: {self.symbol}")
        print(f"[BOT] Trade size: ${self.trade_amount:,.2f} USDT per trade")
        print(f"[BOT] Poll interval: {config.POLL_INTERVAL_SECONDS} seconds")
        print()
    
    def fetch_and_analyze(self) -> dict:
        """
        Fetch market data and calculate indicators.
        
        Returns:
            Dict with DataFrame and latest indicators
        """
        # Fetch latest market data
        self.tracker.fetch_and_cache(self.symbol)
        
        # Get data as DataFrame
        df = self.tracker.get_dataframe(self.symbol, limit=100)
        
        if df.empty:
            return {'df': None, 'indicators': None}
        
        # Calculate all indicators
        df = calculate_all_indicators(df)
        
        # Get latest indicator values
        indicators = get_latest_indicators(df)
        
        return {'df': df, 'indicators': indicators}
    
    def execute_signal(self, signal: Signal, reason: str) -> Optional[dict]:
        """
        Execute a trade based on the strategy signal.
        
        Args:
            signal: BUY, SELL, or HOLD
            reason: Explanation for the signal
        
        Returns:
            Trade result or None if no trade
        """
        if signal == Signal.HOLD:
            return None
        
        position = self.account.get_position(self.symbol)
        
        if signal == Signal.BUY:
            if position is None:
                # Execute buy
                print(f"\n[SIGNAL] BUY - {reason}")
                result = self.executor.market_buy(self.symbol, self.trade_amount)
                if result['success']:
                    self.strategy.on_trade_executed(result)
                return result
            else:
                print(f"[SIGNAL] BUY ignored - already in position")
                return None
        
        elif signal == Signal.SELL:
            if position is not None:
                # Execute sell (entire position)
                print(f"\n[SIGNAL] SELL - {reason}")
                result = self.executor.sell_all(self.symbol)
                if result['success']:
                    self.strategy.on_trade_executed(result)
                return result
            else:
                print(f"[SIGNAL] SELL ignored - no position")
                return None
        
        return None
    
    def run_iteration(self) -> None:
        """
        Run a single iteration of the trading loop.
        """
        self.iteration += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Fetch and analyze
        data = self.fetch_and_analyze()
        
        if data['df'] is None or data['indicators'] is None:
            print(f"[{timestamp}] Waiting for market data...")
            return
        
        df = data['df']
        indicators = data['indicators']
        
        # Get current price
        price = indicators.get('close', 0)
        rsi = indicators.get('rsi', 0)
        
        # Get current position
        position = self.account.get_position(self.symbol)
        
        # Get strategy signal
        result = self.strategy.analyze(df, position)
        signal = result.signal
        
        # Print status
        pos_str = f"Position: {position['amount']:.6f}" if position else "No position"
        print(f"[{timestamp}] {self.symbol}: ${price:,.2f} | RSI: {rsi:.1f} | {pos_str} | Signal: {signal.value}")
        
        # Execute signal
        trade_result = self.execute_signal(signal, result.reason)
        
        # Record equity snapshot
        equity = self.account.record_equity_snapshot()
        
        # Print periodic summary
        if self.iteration % 10 == 0:
            self._print_summary()
    
    def _print_summary(self) -> None:
        """Print a brief status summary."""
        abs_return, pct_return = self.analytics.get_total_return()
        sign = "+" if abs_return >= 0 else ""
        equity = self.account.calculate_total_equity()
        
        print(f"\n--- Iteration {self.iteration} Summary ---")
        print(f"Equity: ${equity:,.2f} ({sign}${abs_return:,.2f} / {sign}{pct_return:.2f}%)")
        print("-" * 35 + "\n")
    
    def run(self, max_iterations: int = None) -> None:
        """
        Run the main trading loop.
        
        Args:
            max_iterations: Stop after N iterations (None = run forever)
        """
        self.running = True
        
        # Set up graceful shutdown
        def signal_handler(sig, frame):
            print("\n\n[BOT] Shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        print("[BOT] Starting trading loop...")
        print("[BOT] Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                # Check iteration limit
                if max_iterations and self.iteration >= max_iterations:
                    print(f"[BOT] Reached max iterations ({max_iterations})")
                    break
                
                # Run one iteration
                self.run_iteration()
                
                # Wait for next poll
                time.sleep(config.POLL_INTERVAL_SECONDS)
        
        except Exception as e:
            print(f"\n[BOT] Error: {e}")
            raise
        
        finally:
            self._shutdown()
    
    def _shutdown(self) -> None:
        """Clean up and show final report."""
        self.running = False
        
        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        
        # Print account status
        self.account.print_status()
        
        # Print trade summary
        self.executor.print_trade_summary()
        
        # Print performance report
        self.analytics.print_report()
        
        # Try to save equity curve
        try:
            self.analytics.plot_equity_curve(
                save_path="data/equity_curve.png",
                show=False
            )
        except Exception as e:
            print(f"[BOT] Could not save equity curve: {e}")
        
        print("[BOT] Shutdown complete")


def run_demo(iterations: int = 20) -> None:
    """
    Run a quick demo of the paper trading system.
    
    This fetches real market data and simulates trading for
    a limited number of iterations.
    
    Args:
        iterations: Number of iterations to run
    """
    print("\n" + "=" * 60)
    print("PAPER TRADING DEMO")
    print("Running for {} iterations".format(iterations))
    print("=" * 60 + "\n")
    
    bot = PaperTradingBot(
        symbol="BTC/USD",
        trade_amount=500.0  # $500 per trade
    )
    
    bot.run(max_iterations=iterations)


def run_backtest_mode() -> None:
    """
    Run in backtest-like mode using cached historical data.
    
    This is faster than real-time as it doesn't wait between iterations.
    """
    print("\n[NOTE] For a proper backtest with historical data,")
    print("       first run the market tracker to cache data,")
    print("       then analyze the cached data offline.\n")
    
    # For now, just run normal mode with reduced iterations
    run_demo(iterations=10)


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    print("""
============================================================
         CRYPTO PAPER TRADING SYSTEM                       
                                                           
  *** PAPER TRADING ONLY - NO REAL MONEY ***               
                                                           
  This system uses:                                        
  - Fake money ($10,000 USDT starting balance)             
  - Real market prices (from Binance public API)           
  - Simulated trade execution                              
                                                           
  NO real wallets, private keys, or live trading!          
============================================================
    """)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            run_demo(iterations=iterations)
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python main.py          # Run continuous paper trading")
            print("  python main.py --demo   # Run 20-iteration demo")
            print("  python main.py --demo N # Run N-iteration demo")
            sys.exit(0)
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # Run continuous paper trading
        bot = PaperTradingBot(
            symbol="BTC/USD",
            trade_amount=500.0
        )
        bot.run()
