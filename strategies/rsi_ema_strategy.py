"""
RSI + EMA Crossover Strategy for the Crypto Paper Trading System.

This strategy combines two popular technical indicators:
- RSI (Relative Strength Index) for overbought/oversold detection
- EMA Crossover for trend direction

Trading Logic:
- BUY: RSI < 30 (oversold) AND fast EMA crosses above slow EMA (bullish)
- SELL: RSI > 70 (overbought) AND fast EMA crosses below slow EMA (bearish)
- HOLD: Otherwise
"""

from typing import Dict, Any, Optional
import pandas as pd

import config
from strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class RsiEmaStrategy(BaseStrategy):
    """
    RSI + EMA Crossover trading strategy.
    
    This strategy generates signals based on:
    1. RSI indicating oversold (< 30) or overbought (> 70) conditions
    2. EMA crossover confirming the trend direction
    
    The combination helps filter out false signals that might occur
    when using either indicator alone.
    
    Parameters (from config):
    - RSI_OVERSOLD: RSI level for buy signal (default: 30)
    - RSI_OVERBOUGHT: RSI level for sell signal (default: 70)
    - EMA_FAST_PERIOD: Fast EMA period (default: 12)
    - EMA_SLOW_PERIOD: Slow EMA period (default: 26)
    """
    
    def __init__(self, 
                 rsi_oversold: float = None,
                 rsi_overbought: float = None):
        """
        Initialize the strategy.
        
        Args:
            rsi_oversold: RSI threshold for oversold (default from config)
            rsi_overbought: RSI threshold for overbought (default from config)
        """
        self.rsi_oversold = rsi_oversold or config.RSI_OVERSOLD
        self.rsi_overbought = rsi_overbought or config.RSI_OVERBOUGHT
        
        # Track last crossover state
        self._last_crossover = None
    
    @property
    def name(self) -> str:
        return "rsi_ema_crossover"
    
    @property
    def description(self) -> str:
        return (
            f"RSI + EMA Crossover Strategy\n"
            f"BUY: RSI < {self.rsi_oversold} AND EMA bullish crossover\n"
            f"SELL: RSI > {self.rsi_overbought} AND EMA bearish crossover"
        )
    
    def analyze(self, df: pd.DataFrame, 
                position: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Analyze market data and generate trading signal.
        
        Args:
            df: DataFrame with OHLCV and indicator data
            position: Current position (or None)
        
        Returns:
            StrategyResult with signal and explanation
        """
        # Need enough data for analysis
        if len(df) < 3:
            return StrategyResult(
                signal=Signal.HOLD,
                reason="Insufficient data for analysis",
                confidence=0
            )
        
        # Check required columns
        required = ['close', 'rsi', 'ema_fast', 'ema_slow']
        missing = [col for col in required if col not in df.columns]
        if missing:
            return StrategyResult(
                signal=Signal.HOLD,
                reason=f"Missing indicators: {missing}",
                confidence=0
            )
        
        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Extract indicator values
        rsi = current['rsi']
        ema_fast = current['ema_fast']
        ema_slow = current['ema_slow']
        prev_ema_fast = previous['ema_fast']
        prev_ema_slow = previous['ema_slow']
        close_price = current['close']
        
        # Check for NaN values
        if pd.isna(rsi) or pd.isna(ema_fast) or pd.isna(ema_slow):
            return StrategyResult(
                signal=Signal.HOLD,
                reason="Indicator values not available yet",
                confidence=0
            )
        
        # Collect indicator values for result
        indicators = {
            'rsi': rsi,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'close': close_price
        }
        
        # Detect EMA crossover
        current_above = ema_fast > ema_slow
        prev_above = prev_ema_fast > prev_ema_slow
        
        bullish_crossover = not prev_above and current_above  # Crossed above
        bearish_crossover = prev_above and not current_above  # Crossed below
        
        # Track crossover state
        if bullish_crossover:
            self._last_crossover = 'bullish'
        elif bearish_crossover:
            self._last_crossover = 'bearish'
        
        # =================================================================
        # BUY SIGNAL
        # Conditions: RSI oversold + EMA bullish (currently or recently)
        # =================================================================
        is_oversold = rsi < self.rsi_oversold
        ema_bullish = current_above or self._last_crossover == 'bullish'
        
        if is_oversold and ema_bullish and position is None:
            # Calculate confidence based on how oversold
            confidence = min(100, (self.rsi_oversold - rsi) * 3 + 50)
            
            return StrategyResult(
                signal=Signal.BUY,
                confidence=confidence,
                reason=f"RSI oversold ({rsi:.1f}) + EMA bullish crossover",
                indicators=indicators
            )
        
        # =================================================================
        # SELL SIGNAL
        # Conditions: RSI overbought + EMA bearish (currently or recently)
        # =================================================================
        is_overbought = rsi > self.rsi_overbought
        ema_bearish = not current_above or self._last_crossover == 'bearish'
        
        if is_overbought and ema_bearish and position is not None:
            # Calculate confidence based on how overbought
            confidence = min(100, (rsi - self.rsi_overbought) * 3 + 50)
            
            return StrategyResult(
                signal=Signal.SELL,
                confidence=confidence,
                reason=f"RSI overbought ({rsi:.1f}) + EMA bearish crossover",
                indicators=indicators
            )
        
        # =================================================================
        # ADDITIONAL SELL CONDITIONS (Risk Management)
        # =================================================================
        if position is not None:
            # Sell if holding and major bearish crossover occurs
            if bearish_crossover and rsi > 50:
                return StrategyResult(
                    signal=Signal.SELL,
                    confidence=60,
                    reason=f"EMA bearish crossover with neutral RSI ({rsi:.1f})",
                    indicators=indicators
                )
        
        # =================================================================
        # HOLD SIGNAL
        # No clear buy or sell conditions
        # =================================================================
        
        # Determine trend for context
        if current_above:
            trend = "bullish"
        else:
            trend = "bearish"
        
        if position is not None:
            reason = f"Holding position. Trend: {trend}, RSI: {rsi:.1f}"
        else:
            reason = f"No position. Trend: {trend}, RSI: {rsi:.1f}"
        
        return StrategyResult(
            signal=Signal.HOLD,
            confidence=50,
            reason=reason,
            indicators=indicators
        )
    
    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """Handle trade execution notification."""
        if trade_result.get('success'):
            side = trade_result['side']
            symbol = trade_result['symbol']
            print(f"[{self.name}] Trade executed: {side} {symbol}")
    
    def reset(self) -> None:
        """Reset strategy state."""
        self._last_crossover = None


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    import numpy as np
    from indicators import calculate_all_indicators
    
    # Create sample data
    np.random.seed(42)
    n = 50
    
    # Simulate price data with a trend
    prices = 100 + np.cumsum(np.random.randn(n) * 2)
    
    df = pd.DataFrame({
        'close': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'open': np.roll(prices, 1),
        'volume': np.random.randint(1000, 10000, n)
    })
    
    # Calculate indicators
    df = calculate_all_indicators(df)
    
    # Create strategy
    strategy = RsiEmaStrategy()
    
    print(f"Strategy: {strategy.name}")
    print(f"Description: {strategy.description}\n")
    
    # Test with no position
    result = strategy.analyze(df, position=None)
    print(f"Signal (no position): {result.signal.value}")
    print(f"Reason: {result.reason}")
    print(f"Confidence: {result.confidence:.1f}%")
    print(f"Indicators: RSI={result.indicators.get('rsi', 0):.1f}")
    
    # Test with a position
    position = {'symbol': 'BTC/USDT', 'amount': 0.1, 'avg_entry_price': 50000}
    result = strategy.analyze(df, position=position)
    print(f"\nSignal (with position): {result.signal.value}")
    print(f"Reason: {result.reason}")
