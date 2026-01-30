"""
Performance Analytics for the Crypto Paper Trading System.

This module provides comprehensive performance metrics:
- Total return
- Win rate
- Max drawdown
- Equity curve visualization
- Trade statistics

All metrics are calculated from the SQLite database history.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import config
import database


class PerformanceAnalytics:
    """
    Performance analytics and visualization for paper trading.
    
    This class calculates key performance metrics:
    - Total Return: Overall percentage gain/loss
    - Win Rate: Percentage of profitable trades
    - Max Drawdown: Largest peak-to-trough decline
    - Sharpe Ratio: Risk-adjusted return (if sufficient data)
    - Profit Factor: Gross profit / Gross loss
    
    It also generates visualizations:
    - Equity curve over time
    - Trade distribution chart
    - Drawdown chart
    """
    
    def __init__(self, starting_balance: float = None):
        """
        Initialize analytics.
        
        Args:
            starting_balance: Initial account balance (default from config)
        """
        self.starting_balance = starting_balance or config.STARTING_BALANCE_USDT
    
    def get_total_return(self) -> Tuple[float, float]:
        """
        Calculate total return.
        
        Returns:
            Tuple of (absolute_return, percentage_return)
        """
        account = database.get_account()
        
        if account is None:
            return (0.0, 0.0)
        
        current_equity = account['total_equity']
        absolute_return = current_equity - self.starting_balance
        percentage_return = (absolute_return / self.starting_balance) * 100
        
        return (absolute_return, percentage_return)
    
    def get_win_rate(self) -> Tuple[float, int, int]:
        """
        Calculate win rate from trade history.
        
        Only considers closed trades (sells) with realized PnL.
        
        Returns:
            Tuple of (win_rate_percent, winning_trades, total_trades)
        """
        trades = database.get_trades(limit=10000)
        
        # Filter to sells only (they have realized PnL)
        sells = [t for t in trades if t['side'] == 'sell']
        
        if not sells:
            return (0.0, 0, 0)
        
        winning_trades = sum(1 for t in sells if t['pnl'] > 0)
        total_trades = len(sells)
        win_rate = (winning_trades / total_trades) * 100
        
        return (win_rate, winning_trades, total_trades)
    
    def get_max_drawdown(self) -> Tuple[float, float]:
        """
        Calculate maximum drawdown from equity history.
        
        Drawdown = (Peak - Trough) / Peak
        
        Returns:
            Tuple of (max_drawdown_percent, max_drawdown_absolute)
        """
        equity_history = database.get_equity_history()
        
        if len(equity_history) < 2:
            return (0.0, 0.0)
        
        # Extract equity values
        equities = [e['equity'] for e in equity_history]
        
        # Calculate running maximum (peak)
        peak = equities[0]
        max_drawdown = 0.0
        max_drawdown_abs = 0.0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown_pct > max_drawdown:
                max_drawdown = drawdown_pct
                max_drawdown_abs = drawdown
        
        return (max_drawdown, max_drawdown_abs)
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """
        Calculate detailed trade statistics.
        
        Returns:
            Dict with various trade metrics
        """
        trades = database.get_trades(limit=10000)
        sells = [t for t in trades if t['side'] == 'sell']
        buys = [t for t in trades if t['side'] == 'buy']
        
        if not sells:
            return {
                'total_trades': len(trades),
                'buys': len(buys),
                'sells': 0,
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'net_profit': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'total_fees': sum(t['fee'] for t in trades)
            }
        
        # Calculate profits and losses
        profits = [t['pnl'] for t in sells if t['pnl'] > 0]
        losses = [t['pnl'] for t in sells if t['pnl'] < 0]
        
        gross_profit = sum(profits) if profits else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        
        avg_profit = np.mean(profits) if profits else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 0.0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        largest_win = max(profits) if profits else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        total_fees = sum(t['fee'] for t in trades)
        
        return {
            'total_trades': len(trades),
            'buys': len(buys),
            'sells': len(sells),
            'winning_trades': len(profits),
            'losing_trades': len(losses),
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': gross_profit - gross_loss,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'total_fees': total_fees
        }
    
    def get_equity_series(self) -> pd.DataFrame:
        """
        Get equity history as a pandas DataFrame.
        
        Returns:
            DataFrame with datetime index and equity column
        """
        history = database.get_equity_history()
        
        if not history:
            return pd.DataFrame()
        
        df = pd.DataFrame(history)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        
        return df
    
    def plot_equity_curve(self, save_path: str = None, show: bool = True) -> None:
        """
        Plot the equity curve over time.
        
        Args:
            save_path: Optional path to save the figure
            show: Whether to display the plot
        """
        df = self.get_equity_series()
        
        if df.empty:
            print("[ANALYTICS] No equity history to plot")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot equity
        ax.plot(df.index, df['equity'], color='#2ecc71', linewidth=2, label='Equity')
        
        # Add starting balance line
        ax.axhline(y=self.starting_balance, color='#3498db', linestyle='--', 
                   label=f'Starting Balance (${self.starting_balance:,.0f})')
        
        # Fill between equity and starting balance
        ax.fill_between(df.index, self.starting_balance, df['equity'],
                        where=(df['equity'] >= self.starting_balance),
                        color='#2ecc71', alpha=0.3)
        ax.fill_between(df.index, self.starting_balance, df['equity'],
                        where=(df['equity'] < self.starting_balance),
                        color='#e74c3c', alpha=0.3)
        
        # Formatting
        ax.set_title('Paper Trading Equity Curve', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('Equity (USDT)')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.xticks(rotation=45)
        
        # Format y-axis with dollar signs
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[ANALYTICS] Equity curve saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_drawdown(self, save_path: str = None, show: bool = True) -> None:
        """
        Plot drawdown over time.
        
        Args:
            save_path: Optional path to save the figure
            show: Whether to display the plot
        """
        df = self.get_equity_series()
        
        if df.empty or len(df) < 2:
            print("[ANALYTICS] Insufficient equity history for drawdown plot")
            return
        
        # Calculate drawdown
        rolling_max = df['equity'].expanding().max()
        drawdown = (rolling_max - df['equity']) / rolling_max * 100
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 4))
        
        # Plot drawdown (inverted for visual clarity)
        ax.fill_between(df.index, 0, -drawdown, color='#e74c3c', alpha=0.7)
        ax.plot(df.index, -drawdown, color='#c0392b', linewidth=1)
        
        # Formatting
        ax.set_title('Drawdown Over Time', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('Drawdown (%)')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def generate_report(self) -> str:
        """
        Generate a text-based performance report.
        
        Returns:
            Formatted report string
        """
        abs_return, pct_return = self.get_total_return()
        win_rate, wins, total = self.get_win_rate()
        max_dd_pct, max_dd_abs = self.get_max_drawdown()
        stats = self.get_trade_statistics()
        
        # Get current equity
        account = database.get_account()
        current_equity = account['total_equity'] if account else self.starting_balance
        
        report = []
        report.append("=" * 60)
        report.append("PAPER TRADING PERFORMANCE REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Account Summary
        report.append("ACCOUNT SUMMARY")
        report.append("-" * 40)
        report.append(f"Starting Balance:    ${self.starting_balance:>12,.2f}")
        report.append(f"Current Equity:      ${current_equity:>12,.2f}")
        sign = "+" if abs_return >= 0 else ""
        report.append(f"Total Return:        ${abs_return:>12,.2f} ({sign}{pct_return:.2f}%)")
        report.append("")
        
        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 40)
        report.append(f"Max Drawdown:        {max_dd_pct:>12.2f}% (${max_dd_abs:,.2f})")
        report.append("")
        
        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Trades:        {stats['total_trades']:>12}")
        report.append(f"  - Buys:            {stats['buys']:>12}")
        report.append(f"  - Sells:           {stats['sells']:>12}")
        report.append(f"Win Rate:            {win_rate:>11.1f}%")
        report.append(f"Winning Trades:      {wins:>12}")
        report.append(f"Losing Trades:       {stats.get('losing_trades', 0):>12}")
        report.append("")
        
        # PnL Breakdown
        report.append("PROFIT & LOSS")
        report.append("-" * 40)
        report.append(f"Gross Profit:        ${stats['gross_profit']:>12,.2f}")
        report.append(f"Gross Loss:          ${stats['gross_loss']:>12,.2f}")
        report.append(f"Net Profit:          ${stats['net_profit']:>12,.2f}")
        report.append(f"Total Fees Paid:     ${stats['total_fees']:>12,.2f}")
        report.append("")
        
        # Trade Analysis
        if stats['sells'] > 0:
            report.append("TRADE ANALYSIS")
            report.append("-" * 40)
            report.append(f"Avg Winning Trade:   ${stats['avg_profit']:>12,.2f}")
            report.append(f"Avg Losing Trade:    ${stats['avg_loss']:>12,.2f}")
            report.append(f"Largest Win:         ${stats['largest_win']:>12,.2f}")
            report.append(f"Largest Loss:        ${stats['largest_loss']:>12,.2f}")
            pf = stats['profit_factor']
            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
            report.append(f"Profit Factor:       {pf_str:>12}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def print_report(self) -> None:
        """Print the performance report to console."""
        print(self.generate_report())


def get_analytics() -> PerformanceAnalytics:
    """
    Factory function to create PerformanceAnalytics instance.
    
    Returns:
        Configured PerformanceAnalytics instance
    """
    return PerformanceAnalytics()


# =============================================================================
# Quick test when run directly
# =============================================================================
if __name__ == "__main__":
    # Create analytics
    analytics = PerformanceAnalytics()
    
    # Print report
    analytics.print_report()
    
    # Try to plot (will show empty message if no data)
    print("\nAttempting to generate equity curve...")
    analytics.plot_equity_curve(show=False, save_path="data/equity_curve.png")
