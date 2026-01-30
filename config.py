"""
Configuration settings for the Crypto Paper Trading System.

This module contains all configurable parameters for the trading system.
IMPORTANT: This is a PAPER TRADING system only - no real money is used.
"""

# =============================================================================
# EXCHANGE SETTINGS
# =============================================================================
# Note: Using Kraken as it has broader geographic availability
# Other options: coinbasepro, gemini, bitfinex, bitstamp
EXCHANGE_ID = "kraken"  # Exchange to use for market data (public API only)

# Trading pairs to track (quote currency should be USD/USDT for paper trading)
# Kraken uses different symbol format: BTC/USD instead of BTC/USDT
TRADING_PAIRS = [
    "BTC/USD",
    "ETH/USD",
]

# Default symbol for single-pair trading
DEFAULT_SYMBOL = "BTC/USD"

# =============================================================================
# MARKET DATA SETTINGS
# =============================================================================
TIMEFRAME = "1m"  # Candlestick timeframe (1 minute)
POLL_INTERVAL_SECONDS = 5  # How often to fetch new market data (5-10 seconds)
CANDLES_TO_FETCH = 100  # Number of candles to fetch per request

# =============================================================================
# PAPER TRADING ACCOUNT SETTINGS
# =============================================================================
STARTING_BALANCE_USDT = 10_000.0  # Initial fake money balance
TRADING_FEE_PERCENT = 0.1  # 0.1% trading fee (Binance standard)

# =============================================================================
# TECHNICAL INDICATOR PARAMETERS
# =============================================================================
# RSI (Relative Strength Index)
RSI_PERIOD = 14

# EMA (Exponential Moving Average)
EMA_FAST_PERIOD = 12
EMA_SLOW_PERIOD = 26

# MACD (Moving Average Convergence Divergence)
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2

# =============================================================================
# STRATEGY PARAMETERS
# =============================================================================
# RSI thresholds for trading signals
RSI_OVERSOLD = 30  # Buy signal when RSI < 30
RSI_OVERBOUGHT = 70  # Sell signal when RSI > 70

# =============================================================================
# DATABASE SETTINGS
# =============================================================================
DATABASE_PATH = "data/crypto_paper.db"

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

# =============================================================================
# SAFETY REMINDERS
# =============================================================================
"""
⚠️  PAPER TRADING ONLY - NO REAL MONEY ⚠️

This system is designed for educational and simulation purposes only.
- All balances are FAKE
- No real cryptocurrency is bought or sold
- No wallet connections
- No private keys
- Only PUBLIC market data is used

Never modify this system to handle real funds.
"""
