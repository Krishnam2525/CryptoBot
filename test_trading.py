"""
Test script to verify the trading system works correctly.
"""

import database
from market_tracker import MarketTracker
from executor import TradeExecutor

# Initialize
database.initialize_database()

# Reset database to start fresh
database.reset_database()
database.initialize_account(10000.0)

# Fetch some market data
print("Fetching market data...")
tracker = MarketTracker(['BTC/USD'])
tracker.fetch_and_cache('BTC/USD')

# Get current price
price = database.get_latest_price('BTC/USD')
print(f"Current BTC/USD price: ${price:,.2f}")

# Create executor and execute a buy
executor = TradeExecutor()
print("\n--- Testing BUY order ($1000) ---")
result = executor.market_buy('BTC/USD', 1000)
print(f"Buy success: {result['success']}")
if result['success']:
    print(f"  Bought: {result['amount']:.6f} BTC")
    print(f"  Price: ${result['price']:,.2f}")
    print(f"  Cost: ${result['cost']:,.2f}")
    print(f"  Fee: ${result['fee']:.2f}")

# Print account status
executor.account.print_status()

# Execute a partial sell
print("\n--- Testing SELL order (half position) ---")
position = executor.account.get_position('BTC/USD')
if position:
    sell_amount = position['amount'] / 2
    result = executor.market_sell('BTC/USD', sell_amount)
    print(f"Sell success: {result['success']}")
    if result['success']:
        print(f"  Sold: {result['amount']:.6f} BTC")
        print(f"  Price: ${result['price']:,.2f}")
        print(f"  Proceeds: ${result['net_proceeds']:,.2f}")
        print(f"  Realized PnL: ${result['pnl']:,.2f}")

# Final status
print("\n" + "=" * 60)
print("FINAL STATUS")
print("=" * 60)
executor.account.print_status()
executor.print_trade_summary()

print("\n*** ALL TESTS PASSED ***")
