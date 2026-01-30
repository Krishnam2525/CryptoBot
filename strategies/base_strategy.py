"""
Base Strategy Interface for the Crypto Paper Trading System.

This module defines the abstract base class for all trading strategies.
Strategies should extend this class and implement the required methods.

The plugin system allows easy addition of new strategies without
modifying the core trading loop.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

import pandas as pd


class Signal(Enum):
    """
    Trading signal enumeration.
    
    Strategies output one of these signals:
    - BUY: Enter a long position
    - SELL: Exit position / Take profit
    - HOLD: No action
    """
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    """
    Result container for strategy analysis.
    
    Attributes:
        signal: The trading signal (BUY, SELL, HOLD)
        confidence: Confidence level 0-100 (optional)
        reason: Human-readable explanation of the signal
        indicators: Dict of indicator values used in decision
    """
    signal: Signal
    confidence: float = 50.0
    reason: str = ""
    indicators: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All trading strategies should inherit from this class and implement:
    - name property: Strategy identifier
    - analyze(): Analyze market data and return a signal
    
    Optional overrides:
    - on_trade_executed(): Called after a trade is executed
    - reset(): Reset strategy state
    
    Example usage:
        class MyStrategy(BaseStrategy):
            @property
            def name(self) -> str:
                return "my_strategy"
            
            def analyze(self, df: pd.DataFrame, position: dict) -> StrategyResult:
                # Your analysis logic here
                return StrategyResult(signal=Signal.HOLD, reason="No conditions met")
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the strategy name.
        
        Returns:
            Unique strategy identifier string
        """
        pass
    
    @property
    def description(self) -> str:
        """
        Get a description of the strategy.
        
        Override this to provide details about the strategy logic.
        
        Returns:
            Strategy description string
        """
        return "No description provided"
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, 
                position: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Analyze market data and generate a trading signal.
        
        This is the main method that strategies must implement.
        It receives market data with indicators and should return
        a signal (BUY, SELL, or HOLD).
        
        Args:
            df: DataFrame with OHLCV data and calculated indicators
                Expected columns: open, high, low, close, volume,
                rsi, ema_fast, ema_slow, macd, macd_signal, etc.
            position: Current position info (or None if no position)
                {'symbol': str, 'amount': float, 'avg_entry_price': float}
        
        Returns:
            StrategyResult with signal and explanation
        """
        pass
    
    def on_trade_executed(self, trade_result: Dict[str, Any]) -> None:
        """
        Called after a trade is executed.
        
        Override this to track trades or update strategy state.
        
        Args:
            trade_result: Result from TradeExecutor
        """
        pass
    
    def reset(self) -> None:
        """
        Reset strategy state.
        
        Override this to clear any internal state when resetting
        the trading session.
        """
        pass
    
    def __str__(self) -> str:
        return f"Strategy({self.name})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
