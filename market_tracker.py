"""
Market Tracker for the Crypto Paper Trading System.

This module handles real-time market data fetching using ccxt.
It connects to Binance (public API only) to get OHLCV candlestick data.

IMPORTANT: Only PUBLIC endpoints are used - no authentication required.
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime

import ccxt
import pandas as pd

import config
import database


class MarketTracker:
    """
    Real-time market data tracker using ccxt.
    
    This class fetches OHLCV (Open, High, Low, Close, Volume) data from
    Binance and caches it locally in SQLite for analysis.
    
    Features:
    - Connects to Binance public API (no auth needed)
    - Fetches 1-minute candlestick data
    - Polls at configurable intervals
    - Caches data to SQLite
    - Handles rate limiting gracefully
    """
    
    def __init__(self, symbols: Optional[List[str]] = None):
        """
        Initialize the market tracker.
        
        Args:
            symbols: List of trading pairs to track (default from config)
        """
        self.symbols = symbols or config.TRADING_PAIRS
        self.timeframe = config.TIMEFRAME
        self.poll_interval = config.POLL_INTERVAL_SECONDS
        
        # Initialize the exchange (Binance - public API only)
        self.exchange = self._create_exchange()
        
        print(f"[MARKET TRACKER] Initialized for {self.symbols}")
        print(f"[MARKET TRACKER] Timeframe: {self.timeframe}, Poll interval: {self.poll_interval}s")
    
    def _create_exchange(self) -> ccxt.Exchange:
        """
        Create and configure the exchange instance.
        
        Returns:
            Configured ccxt exchange object
        """
        # Get the exchange class dynamically
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        
        # Create instance with rate limiting enabled
        exchange = exchange_class({
            'enableRateLimit': True,  # Respect rate limits automatically
            'timeout': 30000,  # 30 second timeout
        })
        
        return exchange
    
    def fetch_ohlcv(self, symbol: str, limit: int = None) -> List[List]:
        """
        Fetch OHLCV candlestick data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            limit: Number of candles to fetch (default from config)
        
        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        limit = limit or config.CANDLES_TO_FETCH
        
        try:
            # Fetch candles from exchange
            # Returns: [[timestamp, open, high, low, close, volume], ...]
            candles = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.timeframe,
                limit=limit
            )
            
            return candles
            
        except ccxt.NetworkError as e:
            print(f"[MARKET TRACKER] Network error fetching {symbol}: {e}")
            return []
        except ccxt.ExchangeError as e:
            print(f"[MARKET TRACKER] Exchange error fetching {symbol}: {e}")
            return []
    
    def fetch_and_cache(self, symbol: str) -> int:
        """
        Fetch OHLCV data and cache it to SQLite.
        
        Args:
            symbol: Trading pair to fetch
        
        Returns:
            Number of candles cached
        """
        candles = self.fetch_ohlcv(symbol)
        
        if candles:
            count = database.save_ohlcv(symbol, candles)
            return count
        
        return 0
    
    def fetch_all_and_cache(self) -> Dict[str, int]:
        """
        Fetch and cache data for all configured symbols.
        
        Returns:
            Dict of {symbol: candle_count}
        """
        results = {}
        
        for symbol in self.symbols:
            count = self.fetch_and_cache(symbol)
            results[symbol] = count
            
            # Small delay between symbols to be nice to the API
            if len(self.symbols) > 1:
                time.sleep(0.5)
        
        return results
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol.
        
        Tries to get from cache first, fetches fresh data if stale.
        
        Args:
            symbol: Trading pair
        
        Returns:
            Current price or None if unavailable
        """
        # First try to get from cache
        cached_price = database.get_latest_price(symbol)
        
        if cached_price is not None:
            return cached_price
        
        # If no cached data, fetch fresh
        candles = self.fetch_ohlcv(symbol, limit=1)
        
        if candles:
            # Return the close price of the most recent candle
            return candles[-1][4]  # Index 4 is close price
        
        return None
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the current ticker information for a symbol.
        
        Args:
            symbol: Trading pair
        
        Returns:
            Ticker dict with last, bid, ask, high, low, volume
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'volume': ticker.get('baseVolume'),
                'timestamp': ticker.get('timestamp')
            }
        except Exception as e:
            print(f"[MARKET TRACKER] Error fetching ticker for {symbol}: {e}")
            return None
    
    def get_dataframe(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Get OHLCV data as a pandas DataFrame.
        
        Args:
            symbol: Trading pair
            limit: Number of candles to retrieve
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Get from cache
        candles = database.get_ohlcv(symbol, limit)
        
        if not candles:
            # Fetch fresh if cache is empty
            raw_candles = self.fetch_ohlcv(symbol, limit)
            if raw_candles:
                database.save_ohlcv(symbol, raw_candles)
                candles = database.get_ohlcv(symbol, limit)
        
        if not candles:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(candles)
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        
        return df
    
    def run_polling_loop(self, callback=None, max_iterations: int = None) -> None:
        """
        Run continuous polling loop for market data.
        
        Args:
            callback: Optional function to call after each poll with results
            max_iterations: Stop after this many iterations (None = infinite)
        
        Example:
            def on_update(results):
                print(f"Updated: {results}")
            
            tracker.run_polling_loop(callback=on_update, max_iterations=10)
        """
        iteration = 0
        
        print(f"[MARKET TRACKER] Starting polling loop (interval: {self.poll_interval}s)")
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                
                # Fetch and cache all symbols
                results = self.fetch_all_and_cache()
                
                # Log the update
                timestamp = datetime.now().strftime("%H:%M:%S")
                for symbol, count in results.items():
                    price = database.get_latest_price(symbol)
                    if price:
                        print(f"[{timestamp}] {symbol}: ${price:,.2f} ({count} candles)")
                
                # Call the callback if provided
                if callback:
                    callback(results)
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n[MARKET TRACKER] Polling stopped by user")


def get_market_tracker(symbols: Optional[List[str]] = None) -> MarketTracker:
    """
    Factory function to create a MarketTracker instance.
    
    Args:
        symbols: Optional list of trading pairs
    
    Returns:
        Configured MarketTracker instance
    """
    return MarketTracker(symbols)


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    # Initialize database
    database.initialize_database()
    
    # Create tracker for BTC/USDT
    tracker = MarketTracker(["BTC/USDT"])
    
    # Fetch and display current price
    price = tracker.get_current_price("BTC/USDT")
    print(f"\nBTC/USDT Current Price: ${price:,.2f}")
    
    # Fetch and cache data
    count = tracker.fetch_and_cache("BTC/USDT")
    print(f"Cached {count} candles")
    
    # Get as DataFrame
    df = tracker.get_dataframe("BTC/USDT", limit=10)
    print(f"\nRecent candles:\n{df}")
