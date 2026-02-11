# Rollout Checklist: IBKR Insync Broker Migration

This checklist guides you through the migration to the new `ib_insync`-based broker.

## Overview

**Status**: Production Ready (v1.5+)  
**Default**: Enabled by default (`IBKR_USE_INSYNC=true`)  
**Rollback**: Immediate (set `IBKR_USE_INSYNC=false`)

## Pre-Migration Checklist

### Environment Verification
- [ ] IB Gateway/TWS is installed and running
- [ ] IB Gateway API is enabled (port 7497 for paper, 7496 for live)
- [ ] Paper trading account is set up (recommended for initial testing)
- [ ] TradeMind server can connect to IB Gateway
  ```bash
  python -c "from ib_insync import IB; ib=IB(); ib.connect('127.0.0.1', 7497, 999); print('OK'); ib.disconnect()"
  ```

### Configuration Backup
- [ ] Backup current `.env` file
  ```bash
  cp .env .env.backup.$(date +%Y%m%d)
  ```
- [ ] Backup custom `config/ibkr_config.yaml` if modified
- [ ] Document any custom configuration changes

### Testing Environment
- [ ] Database is accessible (TimescaleDB running)
- [ ] Redis is accessible and running
- [ ] All unit tests pass
  ```bash
  python run_tests.py --type unit
  ```
- [ ] Paper trading environment is ready

---

## Migration Steps

### Step 1: Verify Current Configuration
```bash
# Check which broker is currently enabled
python -c "from src.config import settings; print('Broker:', 'insync (NEW)' if settings.ibkr_use_insync else 'threaded (OLD)')"

# Check via API (if server running)
curl http://localhost:8000/api/ibkr/status | grep broker_type
```

**Expected**: `broker_type: "insync"` (default since v1.5)

### Step 2: Enable New Broker (if needed)
```bash
# Set environment variable
export IBKR_USE_INSYNC=true

# Or update .env file
echo "IBKR_USE_INSYNC=true" >> .env
```

### Step 3: Verify Configuration Settings
```bash
# Check IBKR settings
python -c "
from src.config import settings
print(f'IBKR Enabled: {settings.ibkr_enabled}')
print(f'Use Insync: {settings.ibkr_use_insync}')
print(f'Reconnect Enabled: {settings.ibkr_insync_reconnect_enabled}')
print(f'Circuit Breaker: {settings.ibkr_circuit_breaker_enabled}')
"
```

### Step 4: Restart Services
```bash
# Stop existing services
pkill -f uvicorn
pkill -f langgraph_auto_trader

# Wait for cleanup
sleep 2

# Start services
docker compose up -d  # If using Docker
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Verify Broker Initialization
```bash
# Check logs for broker type
tail -f logs/*.log | grep -i "ibkr.*broker"

# Should see:
# ✅ IBKR insync broker initialized (connection deferred)
```

### Step 6: Test Connection Status
```bash
# Check API status
curl http://localhost:8000/api/ibkr/status

# Expected response:
# {
#   "enabled": true,
#   "connected": true,
#   "paper_trading": true,
#   "broker_type": "ib_insync",
#   "mode": "paper"
# }
```

### Step 7: Test Account Info
```bash
# Get account summary
curl http://localhost:8000/api/ibkr/account

# Verify:
# - Account ID matches IB Gateway
# - Cash balance is accurate
# - Portfolio value is correct
```

### Step 8: Test Position Sync
```bash
# Sync portfolio with IB Gateway
curl -X POST http://localhost:8000/api/ibkr/sync

# Get positions
curl http://localhost:8000/api/ibkr/positions

# Verify positions match IB Gateway
```

### Step 9: Test Paper Order (Recommended)
```bash
# Place a small test order (paper trading only!)
curl -X POST http://localhost:8000/api/ibkr/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 1,
    "price": 100.00
  }'

# Check order status
curl http://localhost:8000/api/ibkr/orders

# Cancel test order
curl -X DELETE http://localhost:8000/api/ibkr/orders/{order_id}
```

### Step 10: Test Order Cancellation
```bash
# Get open orders
curl http://localhost:8000/api/ibkr/orders

# Cancel an order
curl -X DELETE http://localhost:8000/api/ibkr/orders/{order_id}

# Verify cancellation
curl http://localhost:8000/api/ibkr/orders
```

### Step 11: Test Auto-Trader (if applicable)
```bash
# Start auto-trader
python langgraph_auto_trader.py

# Monitor logs for:
# - IBKR connection establishment
# - Position fetching
# - Trading decisions
# - No deprecation warnings
```

---

## Post-Migration Verification

### Functional Tests
- [ ] Account info retrieved correctly
- [ ] Positions synchronized accurately
- [ ] Orders placed successfully
- [ ] Orders cancelled successfully
- [ ] Order status updates correctly
- [ ] Auto-trader runs without errors
- [ ] Exit strategy triggers work correctly

### Performance Tests
- [ ] Connection time < 3 seconds
- [ ] Order placement latency < 500ms
- [ ] Position fetch < 2 seconds
- [ ] Memory usage stable
- [ ] CPU usage normal

### Log Analysis
```bash
# Check for deprecation warnings (should NOT see any with new broker)
grep -i "deprecated" logs/

# Check for broker type in logs
grep -i "insync broker" logs/

# Check for errors
grep -i "error" logs/

# Check for reconnection events
grep -i "reconnect" logs/
```

### Health Checks
- [ ] `/api/ibkr/status` returns `connected: true`
- [ ] `/health` returns `status: ok`
- [ ] Database accessible
- [ ] Redis accessible
- [ ] IB Gateway still connected

---

## Monitoring Items

### Key Metrics to Monitor
1. **Connection Health**
   - Connection uptime
   - Reconnection attempts
   - Circuit breaker state

2. **Performance Metrics**
   - API response times
   - Order placement latency
   - Position fetch times

3. **Error Rates**
   - Connection errors
   - Order failures
   - API timeouts

### Monitoring Commands
```bash
# Monitor connection status (watch mode)
watch -n 5 'curl -s http://localhost:8000/api/ibkr/status | jq'

# Monitor logs in real-time
tail -f logs/*.log | grep -i "ibkr"

# Monitor memory usage
watch -n 10 'ps aux | grep uvicorn | awk '\''{print $6}'\''

# Monitor circuit breaker state
grep -i "circuit" logs/ | tail -20
```

---

## Rollback Procedure

### When to Rollback
- Frequent connection errors
- Order placement failures
- Performance degradation
- Unexpected errors in logs

### Immediate Rollback Steps
```bash
# 1. Stop services
pkill -f uvicorn
pkill -f langgraph_auto_trader

# 2. Switch to old broker
export IBKR_USE_INSYNC=false
# Or edit .env: IBKR_USE_INSYNC=false

# 3. Restart services
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 4. Verify rollback
curl http://localhost:8000/api/ibkr/status
# Should show: "broker_type": "threaded"

# 5. Test functionality
curl http://localhost:8000/api/ibkr/account
curl http://localhost:8000/api/ibkr/positions
```

### Rollback Verification
- [ ] Old broker is active
- [ ] Connection established
- [ ] Account info retrievable
- [ ] Positions sync correctly
- [ ] Orders can be placed/cancelled

---

## Troubleshooting

### Issue: "Not connected to IB Gateway"
**Cause**: IB Gateway not running or wrong port

**Solution**:
```bash
# Check IB Gateway is running
ps aux | grep ibgateway

# Check port is listening
netstat -an | grep 7497

# Restart IB Gateway if needed
~/ibgateway/start_ibgateway.sh
```

### Issue: Event loop errors
**Cause**: Conflicting event loops or threading issues

**Solution**:
- Ensure using `await` for async calls
- Check for blocking operations in async code
- Verify no event loop conflicts

### Issue: Circuit breaker open
**Cause**: Multiple connection failures

**Solution**:
```bash
# Check circuit breaker state
grep -i "circuit.*open" logs/

# Wait for cooldown (default: 60s)
# Or adjust cooldown in settings
export IBKR_CIRCUIT_BREAKER_COOLDOWN_SECONDS=30
```

### Issue: Deprecation warnings with new broker
**Cause**: Code still importing old broker classes

**Solution**:
```bash
# Check for old broker imports
grep -r "IBKRThreadedBroker" src/
grep -r "from src.brokers.ibkr.async_broker import" src/

# These should only be imported by integration.py
```

---

## Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Pre-Migration** | 1-2 hours | Environment setup, backup, testing |
| **Migration** | 1-2 hours | Switch broker, test endpoints |
| **Verification** | 2-4 hours | Functional tests, monitoring |
| **Monitoring** | 1-2 days | Production observation |
| **Go-Live** | N/A | Full production use |

**Total Estimated Time**: 1-2 days

---

## Support

### Documentation
- Migration Guide: `docs/MIGRATION_TO_IB_INSYNC.md`
- README: `README.md`
- IBKR Integration: `src/brokers/ibkr/`

### Debug Commands
```bash
# Check broker type
python -c "from src.config import settings; print(settings.ibkr_use_insync)"

# Test IB connection
python -c "from ib_insync import IB; ib=IB(); ib.connect('127.0.0.1', 7497, 999); print(ib.managedAccounts()); ib.disconnect()"

# Check ib_insync version
pip show ib_insync

# View IBKR logs
tail -100 logs/trademind.log | grep -i "ibkr"
```

### Report Issues
If you encounter issues:
1. Check this checklist for troubleshooting steps
2. Review logs for error messages
3. Try rollback to old broker
4. Report with:
   - Configuration settings
   - IB Gateway version
   - `ib_insync` version
   - Error messages from logs
   - Steps to reproduce

---

## Success Criteria

Migration is successful when:
- [ ] New broker is active and connected
- [ ] All functional tests pass
- [ ] Performance meets or exceeds old broker
- [ ] No deprecation warnings in logs
- [ ] Monitoring shows stable operation for 24+ hours
- [ ] Auto-trader runs successfully (if applicable)

---

**Last Updated**: 2026-02-10  
**Version**: 1.5  
**Status**: Production Ready
