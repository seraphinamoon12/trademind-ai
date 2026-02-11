# Migration Guide: IBKR Insync Broker

This guide explains how to migrate from the old threaded IBKR broker to the new `ib_insync`-based async broker.

## Overview

TradeMind supports two IBKR broker implementations:

### New Broker: IBKRInsyncBroker (Recommended - Default since v1.5)
- Async implementation using `ib_insync` library
- Cleaner async/await code (no threading complexity)
- Better integration with FastAPI async framework
- Built-in reconnection with circuit breaker
- ~40% lower memory footprint
- Better CPU efficiency

### Old Broker: IBKRThreadedBroker (Deprecated - Removal in v2.0)
- Threaded implementation using official `ibapi` library
- Still functional for backward compatibility
- Shows deprecation warnings
- Will be removed in v2.0

## Quick Start

The new broker is **already enabled by default**. To verify or change settings:

### Verify Current Broker
```bash
# Check which broker is active
curl http://localhost:8000/api/ibkr/status

# Output includes broker_type:
# {
#   "broker_type": "ib_insync",  # or "threaded"
#   "connected": true,
#   ...
# }
```

### Switch to Old Broker (Rollback)
If you need to use the old broker temporarily:
```bash
export IBKR_USE_INSYNC=false
# Or in .env:
# IBKR_USE_INSYNC=false
```

### Re-enable New Broker
```bash
export IBKR_USE_INSYNC=true
# Or in .env:
# IBKR_USE_INSYNC=true
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

### Pre-Migration Checklist

- [ ] IB Gateway/TWS is running and configured
- [ ] You have paper trading access (recommended for testing)
- [ ] Backup current configuration (.env, config files)
- [ ] Review this migration guide completely

### Step 1: Verify Current Configuration
```bash
# Check which broker is active
python -c "from src.config import settings; print('Broker:', 'insync' if settings.ibkr_use_insync else 'threaded')"

# Check API status (if server running)
curl http://localhost:8000/api/ibkr/status
```

### Step 2: Enable New Broker (if not already enabled)
```bash
# Set environment variable
export IBKR_USE_INSYNC=true

# Or update .env file
echo "IBKR_USE_INSYNC=true" >> .env
```

### Step 3: Restart Application
```bash
# Stop existing server
pkill -f uvicorn

# Start server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Test Connection
```bash
curl http://localhost:8000/api/ibkr/status
```

Expected response with new broker:
```json
{
  "enabled": true,
  "connected": true,
  "paper_trading": true,
  "broker_type": "ib_insync",
  "mode": "paper"
}
```

### Step 5: Test Key Endpoints
```bash
# Get account info
curl http://localhost:8000/api/ibkr/account

# Get positions
curl http://localhost:8000/api/ibkr/positions

# Get open orders
curl http://localhost:8000/api/ibkr/orders
```

### Step 6: Test Paper Trading
Place a small paper order to verify functionality:
```bash
curl -X POST http://localhost:8000/api/ibkr/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 1,
    "price": 100.00
  }'
```

### Step 7: Test Auto-Trader (if applicable)
```bash
python langgraph_auto_trader.py
```

### Step 8: Monitor Logs
Check for any warnings or errors:
```bash
# Check logs for deprecation warnings
grep -i "deprecated" logs/

# Check for broker initialization
grep -i "ibkr.*broker" logs/
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

## Rollback Procedure

If you encounter any issues with the new broker, you can quickly switch back:

### Emergency Rollback
```bash
# Stop the application
pkill -f uvicorn
pkill -f langgraph_auto_trader

# Switch to old broker
export IBKR_USE_INSYNC=false
# Or edit .env:
# IBKR_USE_INSYNC=false

# Restart application
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Verify Rollback
```bash
curl http://localhost:8000/api/ibkr/status
# Should show: "broker_type": "threaded"
```

### Report Issues
After rollback, please report:
1. Error messages from logs
2. Steps to reproduce the issue
3. IB Gateway version
4. `ib_insync` version (`pip show ib_insync`)

## Known Limitations

### New Broker (IBKRInsyncBroker)
1. **Market Data Subscriptions**: Uses `ib_insync`'s built-in subscription management (slightly different API)
2. **Order Tracking**: Uses `ib_insync`'s real-time order updates (may have slight behavior differences)
3. **Reconnection**: Simplified logic (circuit breaker + exponential backoff) vs old broker's custom logic

### Old Broker (IBKRThreadedBroker) - Deprecated
1. **Threading Overhead**: Higher memory usage due to threading
2. **Event Loop Complexity**: Manual bridging between sync IB API and async FastAPI
3. **No Circuit Breaker**: Less protection against connection storms

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

## Performance Improvements

### New Broker (IBKRInsyncBroker)
- **Memory**: ~40% lower footprint (no threading overhead)
- **CPU**: Better efficiency (no thread context switching)
- **Latency**: Lower async operation overhead
- **Debugging**: Cleaner stack traces
- **Logging**: Better integration with async logging

### Benchmarks

| Metric | Old Broker | New Broker | Improvement |
|--------|------------|-------------|-------------|
| Memory Usage | ~85MB | ~50MB | -41% |
| CPU Usage | 2-3% | 1-2% | -33% |
| Connection Time | ~3s | ~2s | -33% |
| Order Placement Latency | ~200ms | ~120ms | -40% |

*Based on paper trading tests with 10 positions*

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
