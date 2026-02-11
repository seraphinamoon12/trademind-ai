# Migration Guide: IBKR Insync Broker

This guide explains how to migrate from the old threaded IBKR broker to the new `ib_insync`-based async broker.

## Overview

TradeMind now supports two IBKR broker implementations:
- **Old Broker** (`IBKRThreadedBroker`): Threaded implementation using the official `ibapi` library
- **New Broker** (`IBKRInsyncBroker`): Async implementation using the `ib_insync` library

The new broker provides:
- Cleaner async/await code (no threading complexity)
- Better integration with FastAPI async framework
- Simplified error handling
- Built-in reconnection logic
- Cleaner event loop management

## Quick Start

To enable the new broker, update your configuration:

### Method 1: Environment Variable
```bash
export IBKR_USE_INSYNC=true
```

### Method 2: Settings File (`src/config.py`)
The setting is already configured to use the new broker by default:
```python
ibkr_use_insync: bool = Field(default=True)
```

### Method 3: `.env` File
```env
IBKR_USE_INSYNC=true
```

## Configuration Options

The new broker has its own configuration section in `src/config.py`:

```python
# IBKR Insync Configuration
ibkr_use_insync: bool = Field(default=True)  # Enable new broker
ibkr_insync_reconnect_enabled: bool = Field(default=True)  # Auto-reconnect
ibkr_insync_max_reconnect_attempts: int = Field(default=5)  # Max reconnection attempts
ibkr_insync_reconnect_backoff: int = Field(default=5)  # Backoff in seconds
ibkr_insync_connect_timeout: int = Field(default=10)  # Connection timeout
ibkr_insync_lazy_connect: bool = Field(default=True)  # Lazy connection
```

## How Switching Works

The `IBKRIntegration` class automatically selects the appropriate broker based on `ibkr_use_insync`:

```python
# From src/brokers/ibkr/integration.py
if settings.ibkr_use_insync:
    from src.brokers.ibkr.ibkr_insync_broker import IBKRInsyncBroker
    self._broker = IBKRInsyncBroker(...)
else:
    from src.brokers.ibkr.async_broker import IBKRThreadedBroker
    self._broker = IBKRThreadedBroker(...)
```

All API endpoints and the auto-trader use `IBKRIntegration`, so the broker switching is transparent.

## Migration Steps

### 1. Verify Current Configuration
Check which broker is currently enabled:
```bash
# Check environment variable
echo $IBKR_USE_INSYNC

# Or check settings
python -c "from src.config import settings; print(settings.ibkr_use_insync)"
```

### 2. Enable New Broker (if not already enabled)
Set `ibkr_use_insync=True` in your configuration.

### 3. Test Connection
Start the API server and test connection:
```bash
curl http://localhost:8000/api/ibkr/status
```

Expected response with new broker:
```json
{
  "enabled": true,
  "connected": true,
  "paper_trading": true,
  "mode": "paper"
}
```

### 4. Test Key Endpoints
Test all IBKR endpoints to ensure compatibility:

```bash
# Connect to IBKR
curl -X POST http://localhost:8000/api/ibkr/connect

# Get account info
curl http://localhost:8000/api/ibkr/account

# Get positions
curl http://localhost:8000/api/ibkr/positions

# Get open orders
curl http://localhost:8000/api/ibkr/orders

# Disconnect
curl -X POST http://localhost:8000/api/ibkr/disconnect
```

### 5. Test Auto-Trader
If using the auto-trader, verify it works with the new broker:
```bash
python langgraph_auto_trader.py
```

## Switching Back (Rollback)

If you encounter issues, you can switch back to the old broker:

```bash
export IBKR_USE_INSYNC=false
```

Or update `src/config.py`:
```python
ibkr_use_insync: bool = Field(default=False)
```

Then restart your application.

## Known Limitations

1. **Reconnection Logic**: The new broker's reconnection logic is simpler. If you need advanced reconnection, use the old broker.

2. **Market Data Subscriptions**: Both brokers support market data, but the new broker uses `ib_insync`'s built-in subscription management.

3. **Order Management**: The new broker uses `ib_insync`'s trade tracking, which may have slightly different behavior than the old broker's manual tracking.

## Troubleshooting

### Issue: "Not connected to IB Gateway" errors

**Solution**: Ensure lazy connection is working correctly:
- The new broker uses lazy connection by default
- Connection is established on first API call
- Check IB Gateway/TWS is running on correct port

### Issue: Event loop errors

**Solution**: The new broker is designed to work with FastAPI's async framework. If you see event loop errors:
- Ensure you're using `await` when calling broker methods
- Don't mix blocking code with async operations

### Issue: Position data discrepancies

**Solution**: The new broker may return slightly different position data:
- `current_price` may be 0 if market data not available
- `market_value` and `unrealized_pnl` are calculated differently
- Compare both brokers' output during transition

### Issue: Order status not updating

**Solution**: The new broker uses `ib_insync`'s real-time order updates:
- Check that order status polling interval is appropriate
- Ensure IB Gateway is sending order updates
- Verify order ID format (integers in new broker vs strings in old)

## Testing Checklist

Before switching to production use:

- [ ] IB Gateway/TWS is running
- [ ] Connection successful (`/api/ibkr/status` shows `connected: true`)
- [ ] Account info retrieved correctly
- [ ] Positions listed accurately
- [ ] Open orders shown correctly
- [ ] Market data retrieved for test symbols
- [ ] Paper trading order placed successfully
- [ ] Order cancelled successfully
- [ ] Auto-trader initializes without errors
- [ ] Auto-trader fetches positions correctly
- [ ] Auto-trader makes trading decisions
- [ ] Exit strategy triggers work correctly

## API Compatibility

The new broker is fully compatible with all existing API endpoints:

| Endpoint | New Broker Support |
|----------|-------------------|
| `GET /api/ibkr/status` | ✅ |
| `POST /api/ibkr/connect` | ✅ |
| `POST /api/ibkr/disconnect` | ✅ |
| `GET /api/ibkr/account` | ✅ |
| `GET /api/ibkr/positions` | ✅ |
| `GET /api/ibkr/orders` | ✅ |
| `GET /api/ibkr/orders/{order_id}` | ✅ |
| `DELETE /api/ibkr/orders/{order_id}` | ✅ |
| `POST /api/ibkr/orders` | ✅ |
| `GET /api/ibkr/quote/{symbol}` | ✅ |
| `POST /api/ibkr/sync` | ✅ |

## Performance Considerations

### New Broker Advantages:
- Lower memory footprint (no threading overhead)
- Better CPU efficiency (no thread context switching)
- Cleaner stack traces for debugging
- Better integration with async logging

### Old Broker Advantages:
- More battle-tested
- Manual control over threading
- Established error handling patterns

## Monitoring

When using the new broker, monitor:

1. **Connection Status**: Check logs for connection/reconnection events
2. **Order Latency**: Monitor order placement and fill times
3. **API Response Times**: Track endpoint performance
4. **Error Rates**: Watch for any new error patterns

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify IB Gateway/TWS configuration
3. Try switching back to the old broker
4. Report issues with:
   - Configuration settings
   - IB Gateway version
   - `ib_insync` version
   - Error messages from logs

## Version Compatibility

- **IB Gateway**: Tested with version 10.19+
- **ib_insync**: Tested with version 0.13.3+
- **Python**: Requires Python 3.9+

## References

- IBKR Integration: `src/brokers/ibkr/integration.py`
- New Broker: `src/brokers/ibkr/ibkr_insync_broker.py`
- Old Broker: `src/brokers/ibkr/async_broker.py`
- Base Interface: `src/brokers/base.py`
- API Routes: `src/api/routes/ibkr_trading.py`
