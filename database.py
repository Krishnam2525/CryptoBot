"""
SQLite Database Management for the Crypto Paper Trading System.

This module handles all database operations including:
- Database initialization and schema creation
- OHLCV market data storage and retrieval
- Trade history logging
- Position tracking
- Account state persistence
- Equity history for performance analysis
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
import config


def get_connection() -> sqlite3.Connection:
    """
    Get a database connection, creating the database file if needed.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    # Ensure data directory exists
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn


def initialize_database() -> None:
    """
    Initialize the database with all required tables.
    Call this once at application startup.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # ==========================================================================
    # OHLCV Market Data Table
    # Stores candlestick data fetched from the exchange
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            UNIQUE(symbol, timestamp)
        )
    """)
    
    # Index for faster queries by symbol and timestamp
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timestamp 
        ON ohlcv(symbol, timestamp DESC)
    """)
    
    # ==========================================================================
    # Trades Table
    # Logs every simulated trade with full details
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            fee REAL NOT NULL,
            timestamp INTEGER NOT NULL,
            pnl REAL DEFAULT 0
        )
    """)
    
    # ==========================================================================
    # Positions Table
    # Tracks currently open positions
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            avg_entry_price REAL NOT NULL,
            unrealized_pnl REAL DEFAULT 0
        )
    """)
    
    # ==========================================================================
    # Account Table
    # Stores the current account state (single row)
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            cash_balance REAL NOT NULL,
            total_equity REAL NOT NULL,
            last_updated INTEGER NOT NULL
        )
    """)
    
    # ==========================================================================
    # Equity History Table
    # Tracks equity over time for performance analysis
    # ==========================================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            equity REAL NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("[DATABASE] Initialized successfully")


# =============================================================================
# OHLCV DATA OPERATIONS
# =============================================================================

def save_ohlcv(symbol: str, candles: List[List]) -> int:
    """
    Save OHLCV candlestick data to the database.
    Uses INSERT OR REPLACE to handle duplicates.
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        candles: List of [timestamp, open, high, low, close, volume]
    
    Returns:
        Number of candles inserted/updated
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for candle in candles:
        timestamp, open_price, high, low, close, volume = candle
        cursor.execute("""
            INSERT OR REPLACE INTO ohlcv 
            (symbol, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, timestamp, open_price, high, low, close, volume))
        count += 1
    
    conn.commit()
    conn.close()
    return count


def get_ohlcv(symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve recent OHLCV data for a symbol.
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        limit: Maximum number of candles to retrieve
    
    Returns:
        List of candle dictionaries ordered by timestamp (oldest first)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (symbol, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts and reverse to get oldest first
    candles = [dict(row) for row in rows]
    candles.reverse()
    return candles


def get_latest_price(symbol: str) -> Optional[float]:
    """
    Get the most recent close price for a symbol.
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
    
    Returns:
        Latest close price or None if no data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT close FROM ohlcv
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (symbol,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['close'] if row else None


# =============================================================================
# TRADE OPERATIONS
# =============================================================================

def log_trade(symbol: str, side: str, amount: float, price: float, 
              fee: float, pnl: float = 0) -> int:
    """
    Log a simulated trade to the database.
    
    Args:
        symbol: Trading pair
        side: "buy" or "sell"
        amount: Amount of crypto traded
        price: Execution price
        fee: Trading fee in USDT
        pnl: Realized PnL (for sells)
    
    Returns:
        Trade ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = int(datetime.now().timestamp() * 1000)
    
    cursor.execute("""
        INSERT INTO trades (symbol, side, amount, price, fee, timestamp, pnl)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (symbol, side, amount, price, fee, timestamp, pnl))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return trade_id


def get_trades(symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve trade history.
    
    Args:
        symbol: Filter by symbol (optional)
        limit: Maximum trades to retrieve
    
    Returns:
        List of trade dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if symbol:
        cursor.execute("""
            SELECT * FROM trades
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, limit))
    else:
        cursor.execute("""
            SELECT * FROM trades
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# =============================================================================
# POSITION OPERATIONS
# =============================================================================

def get_position(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get the current position for a symbol.
    
    Args:
        symbol: Trading pair
    
    Returns:
        Position dict or None if no position
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM positions WHERE symbol = ?
    """, (symbol,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def update_position(symbol: str, amount: float, avg_entry_price: float) -> None:
    """
    Update or create a position.
    
    Args:
        symbol: Trading pair
        amount: Position size (0 to close position)
        avg_entry_price: Average entry price
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if amount <= 0:
        # Close position
        cursor.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO positions (symbol, amount, avg_entry_price, unrealized_pnl)
            VALUES (?, ?, ?, 0)
        """, (symbol, amount, avg_entry_price))
    
    conn.commit()
    conn.close()


def get_all_positions() -> List[Dict[str, Any]]:
    """
    Get all open positions.
    
    Returns:
        List of position dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM positions WHERE amount > 0")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# =============================================================================
# ACCOUNT OPERATIONS
# =============================================================================

def get_account() -> Optional[Dict[str, Any]]:
    """
    Get the current account state.
    
    Returns:
        Account dict or None if not initialized
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM account WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def update_account(cash_balance: float, total_equity: float) -> None:
    """
    Update the account state.
    
    Args:
        cash_balance: Available USDT balance
        total_equity: Total portfolio value (cash + positions)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = int(datetime.now().timestamp() * 1000)
    
    cursor.execute("""
        INSERT OR REPLACE INTO account (id, cash_balance, total_equity, last_updated)
        VALUES (1, ?, ?, ?)
    """, (cash_balance, total_equity, timestamp))
    
    conn.commit()
    conn.close()


def initialize_account(starting_balance: float) -> None:
    """
    Initialize the account with starting balance.
    Only creates if account doesn't exist.
    
    Args:
        starting_balance: Initial USDT balance
    """
    if get_account() is None:
        update_account(starting_balance, starting_balance)
        print(f"[ACCOUNT] Initialized with ${starting_balance:,.2f} USDT")


# =============================================================================
# EQUITY HISTORY OPERATIONS
# =============================================================================

def record_equity(equity: float) -> None:
    """
    Record current equity for performance tracking.
    
    Args:
        equity: Current total equity value
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = int(datetime.now().timestamp() * 1000)
    
    cursor.execute("""
        INSERT INTO equity_history (timestamp, equity)
        VALUES (?, ?)
    """, (timestamp, equity))
    
    conn.commit()
    conn.close()


def get_equity_history() -> List[Dict[str, Any]]:
    """
    Get full equity history for performance analysis.
    
    Returns:
        List of {timestamp, equity} dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, equity FROM equity_history
        ORDER BY timestamp ASC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def reset_database() -> None:
    """
    Reset all data in the database.
    WARNING: This deletes all trades, positions, and history!
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM trades")
    cursor.execute("DELETE FROM positions")
    cursor.execute("DELETE FROM account")
    cursor.execute("DELETE FROM equity_history")
    cursor.execute("DELETE FROM ohlcv")
    
    conn.commit()
    conn.close()
    print("[DATABASE] All data reset")
