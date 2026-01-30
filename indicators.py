"""
Technical Indicators for the Crypto Paper Trading System.

This module provides calculations for common technical indicators:
- RSI (Relative Strength Index)
- EMA (Exponential Moving Average)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands

All calculations use pandas and numpy for efficiency.
"""

import numpy as np
import pandas as pd
from typing import Tuple

import config


def calculate_rsi(prices: pd.Series, period: int = None) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI).
    
    RSI measures the speed and magnitude of price changes to evaluate
    overbought or oversold conditions.
    
    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
    
    Interpretation:
        - RSI > 70: Overbought (potential sell signal)
        - RSI < 30: Oversold (potential buy signal)
    
    Args:
        prices: Series of closing prices
        period: RSI period (default from config)
    
    Returns:
        Series of RSI values (0-100)
    """
    period = period or config.RSI_PERIOD
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gains = delta.copy()
    losses = delta.copy()
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = abs(losses)
    
    # Calculate rolling averages using Wilder's smoothing method
    avg_gain = gains.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Handle division by zero (when avg_loss is 0)
    rsi = rsi.replace([np.inf, -np.inf], 100)
    rsi = rsi.fillna(50)  # Neutral RSI when no data
    
    return rsi


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA).
    
    EMA gives more weight to recent prices, making it more responsive
    to new information than a simple moving average.
    
    Formula:
        EMA = Price(t) * k + EMA(t-1) * (1 - k)
        k = 2 / (period + 1)
    
    Args:
        prices: Series of closing prices
        period: EMA period
    
    Returns:
        Series of EMA values
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_ema_fast(prices: pd.Series) -> pd.Series:
    """
    Calculate the fast EMA using the configured period.
    
    Args:
        prices: Series of closing prices
    
    Returns:
        Series of fast EMA values
    """
    return calculate_ema(prices, config.EMA_FAST_PERIOD)


def calculate_ema_slow(prices: pd.Series) -> pd.Series:
    """
    Calculate the slow EMA using the configured period.
    
    Args:
        prices: Series of closing prices
    
    Returns:
        Series of slow EMA values
    """
    return calculate_ema(prices, config.EMA_SLOW_PERIOD)


def calculate_macd(prices: pd.Series, 
                   fast_period: int = None,
                   slow_period: int = None,
                   signal_period: int = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    MACD is a trend-following momentum indicator that shows the
    relationship between two moving averages of prices.
    
    Components:
        - MACD Line: Fast EMA - Slow EMA
        - Signal Line: EMA of MACD Line
        - Histogram: MACD Line - Signal Line
    
    Interpretation:
        - MACD crosses above signal: Bullish (buy signal)
        - MACD crosses below signal: Bearish (sell signal)
        - Histogram positive/growing: Bullish momentum
        - Histogram negative/shrinking: Bearish momentum
    
    Args:
        prices: Series of closing prices
        fast_period: Fast EMA period (default from config)
        slow_period: Slow EMA period (default from config)
        signal_period: Signal line period (default from config)
    
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    fast_period = fast_period or config.MACD_FAST_PERIOD
    slow_period = slow_period or config.MACD_SLOW_PERIOD
    signal_period = signal_period or config.MACD_SIGNAL_PERIOD
    
    # Calculate EMAs
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    # Calculate MACD line
    macd_line = fast_ema - slow_ema
    
    # Calculate signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series,
                               period: int = None,
                               std_dev: float = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Bollinger Bands consist of a middle band (SMA) with upper and lower
    bands at a specified number of standard deviations away.
    
    Components:
        - Middle Band: Simple Moving Average
        - Upper Band: Middle Band + (std_dev * Standard Deviation)
        - Lower Band: Middle Band - (std_dev * Standard Deviation)
    
    Interpretation:
        - Price near upper band: Potentially overbought
        - Price near lower band: Potentially oversold
        - Band squeeze: Low volatility, potential breakout
        - Band expansion: High volatility
    
    Args:
        prices: Series of closing prices
        period: Rolling period for SMA and std dev (default from config)
        std_dev: Number of standard deviations (default from config)
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    period = period or config.BB_PERIOD
    std_dev = std_dev or config.BB_STD_DEV
    
    # Calculate middle band (Simple Moving Average)
    middle_band = prices.rolling(window=period).mean()
    
    # Calculate standard deviation
    rolling_std = prices.rolling(window=period).std()
    
    # Calculate upper and lower bands
    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)
    
    return upper_band, middle_band, lower_band


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators and add them to the DataFrame.
    
    This is the main function to use when you need all indicators
    computed at once. It expects a DataFrame with at least a 'close' column.
    
    Args:
        df: DataFrame with OHLCV data (must have 'close' column)
    
    Returns:
        DataFrame with additional columns for all indicators:
        - rsi: Relative Strength Index
        - ema_fast: Fast Exponential Moving Average
        - ema_slow: Slow Exponential Moving Average
        - macd: MACD Line
        - macd_signal: MACD Signal Line
        - macd_histogram: MACD Histogram
        - bb_upper: Bollinger Band Upper
        - bb_middle: Bollinger Band Middle
        - bb_lower: Bollinger Band Lower
    """
    if df.empty or 'close' not in df.columns:
        return df
    
    # Make a copy to avoid modifying the original
    result = df.copy()
    
    # RSI
    result['rsi'] = calculate_rsi(result['close'])
    
    # EMAs
    result['ema_fast'] = calculate_ema_fast(result['close'])
    result['ema_slow'] = calculate_ema_slow(result['close'])
    
    # MACD
    macd, signal, histogram = calculate_macd(result['close'])
    result['macd'] = macd
    result['macd_signal'] = signal
    result['macd_histogram'] = histogram
    
    # Bollinger Bands
    upper, middle, lower = calculate_bollinger_bands(result['close'])
    result['bb_upper'] = upper
    result['bb_middle'] = middle
    result['bb_lower'] = lower
    
    return result


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """
    Get the most recent indicator values as a dictionary.
    
    Useful for making trading decisions based on current indicator values.
    
    Args:
        df: DataFrame with calculated indicators
    
    Returns:
        Dict with latest values for all indicators
    """
    if df.empty:
        return {}
    
    # Get the last row
    last = df.iloc[-1]
    
    indicators = {
        'close': last.get('close'),
        'rsi': last.get('rsi'),
        'ema_fast': last.get('ema_fast'),
        'ema_slow': last.get('ema_slow'),
        'macd': last.get('macd'),
        'macd_signal': last.get('macd_signal'),
        'macd_histogram': last.get('macd_histogram'),
        'bb_upper': last.get('bb_upper'),
        'bb_middle': last.get('bb_middle'),
        'bb_lower': last.get('bb_lower'),
    }
    
    # Clean up NaN values
    return {k: (v if pd.notna(v) else None) for k, v in indicators.items()}


def detect_ema_crossover(df: pd.DataFrame) -> str:
    """
    Detect EMA crossover signals.
    
    Args:
        df: DataFrame with ema_fast and ema_slow columns
    
    Returns:
        'bullish' if fast crosses above slow,
        'bearish' if fast crosses below slow,
        'none' otherwise
    """
    if len(df) < 2:
        return 'none'
    
    if 'ema_fast' not in df.columns or 'ema_slow' not in df.columns:
        return 'none'
    
    # Get current and previous values
    current_fast = df['ema_fast'].iloc[-1]
    current_slow = df['ema_slow'].iloc[-1]
    prev_fast = df['ema_fast'].iloc[-2]
    prev_slow = df['ema_slow'].iloc[-2]
    
    # Check for NaN
    if pd.isna(current_fast) or pd.isna(current_slow):
        return 'none'
    if pd.isna(prev_fast) or pd.isna(prev_slow):
        return 'none'
    
    # Detect crossover
    if prev_fast <= prev_slow and current_fast > current_slow:
        return 'bullish'  # Golden cross
    elif prev_fast >= prev_slow and current_fast < current_slow:
        return 'bearish'  # Death cross
    
    return 'none'


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    # Create sample price data for testing
    np.random.seed(42)
    n = 100
    
    # Simulate a random walk price series
    returns = np.random.randn(n) * 0.02  # 2% daily volatility
    prices = 100 * np.exp(np.cumsum(returns))
    
    # Create DataFrame
    df = pd.DataFrame({
        'close': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'open': np.roll(prices, 1),
        'volume': np.random.randint(1000, 10000, n)
    })
    
    # Calculate all indicators
    df_with_indicators = calculate_all_indicators(df)
    
    print("Sample data with indicators:")
    print(df_with_indicators.tail(10))
    
    print("\nLatest indicators:")
    latest = get_latest_indicators(df_with_indicators)
    for key, value in latest.items():
        if value is not None:
            print(f"  {key}: {value:.4f}")
