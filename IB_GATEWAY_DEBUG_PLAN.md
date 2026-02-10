# IB Gateway Integration - Debugging & Implementation Plan

## Executive Summary

**Current Status:** The new `ibapi`-based client has been implemented but still has event loop conflicts with FastAPI. The client can connect to IB Gateway but hangs during data retrieval.

**Goal:** Fix the event loop conflicts to enable proper IB Gateway integration with TradeMind's FastAPI server.

---

## 1. Diagnostic Checklist

### 1.1 Verify IB Gateway Status
```bash
# Check if IB Gateway is listening on port 7497
ss -tlnp | grep 7497

# Expected output:
# LISTEN 0 50 *:7497 *:* users:(("java",pid=...,fd=...))
```

### 1.2 Test Client in Isolation
```python
# test_ib_client.py
import asyncio
import sys
sys.path.insert(0, 'src')

from brokers.ibkr.client import IBKRBroker

async def test():
    broker = IBKRBroker(host='127.0.0.1', port=7497, client_id=10)
    print("Connecting...")
    connected = await broker.connect()
    print(f"Connected: {connected}")
    
    if connected:
        print("Getting account...")
        account = await broker.get_account()
        print(f"Account: {account}")
        await broker.disconnect()

asyncio.run(test())
```

### 1.3 Check Event Loop State
```python
import asyncio
print(f"Current loop: {asyncio.get_event_loop()}")
print(f"Loop running: {asyncio.get_event_loop().is_running()}")
```

---

## 2. Root Cause Analysis

### 2.1 Identified Issues

**Issue 1: Event Loop Conflicts**
- `ibapi` uses synchronous socket operations
- `asyncio.to_thread()` runs code in thread pool
- But `ibapi` callbacks may reference the wrong event loop

**Issue 2: Blocking Operations**
- `EClient.run()` blocks forever
- `asyncio.to_thread()` can't handle infinite loops
- Need to run client in separate thread with its own loop

**Issue 3: Thread Safety**
- `ibapi` callbacks happen in client's thread
- FastAPI expects callbacks in main thread
- Need thread-safe queue mechanism

### 2.2 Why Current Implementation Fails

```python
# Current approach (FAILS):
async def connect(self):
    def _connect_sync():
        self.client.connect(...)  # Blocks!
        self.client.run()          # Blocks forever!
    
    await asyncio.to_thread(_connect_sync)  # Never returns
```

**Problem:** `client.run()` blocks the thread forever, so `asyncio.to_thread()` never returns.

---

## 3. Solution Options

### Option A: Separate Thread with Queue (RECOMMENDED)

**Architecture:**
```
Main Thread (FastAPI)          Client Thread
    |                              |
    |--- async call --->|          |
    |                   |-- queue ->| 
    |                   |          |--- ibapi calls
    |<-- response ------|<- queue--|
    |                              |
```

**Pros:**
- Clean separation of concerns
- No event loop conflicts
- Thread-safe communication
- Can handle infinite client loop

**Cons:**
- More complex implementation
- Requires queue management

**Implementation Sketch:**
```python
class IBKRClientThread(threading.Thread):
    def __init__(self):
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
    def run(self):
        # Run ibapi in this thread
        self.client.connect()
        while self.running:
            # Process requests from queue
            # Send responses back
            self.client.run()  # Blocks here, but that's OK
```

---

### Option B: Process-based Isolation

**Architecture:**
```
FastAPI Process          IB Client Process
    |                         |
    |--- IPC call --------->| |
    |                       | |--- ibapi
    |<-- response ----------| |
```

**Pros:**
- Complete isolation
- No shared memory issues
- Can restart client independently

**Cons:**
- Much more complex
- IPC overhead
- Process management needed

---

### Option C: FastAPI Background Tasks

**Architecture:**
```python
@app.on_event("startup")
async def startup():
    # Run IB client in background
    asyncio.create_task(ib_client_loop())

async def ib_client_loop():
    while True:
        await asyncio.sleep(0.1)
        # Process pending requests
```

**Pros:**
- Simple to implement
- Uses FastAPI's event loop

**Cons:**
- May still have event loop conflicts
- Hard to debug

---

## 4. Recommended Approach: Option A (Separate Thread)

### 4.1 File Changes Required

1. **src/brokers/ibkr/client.py** - Complete rewrite with thread-based architecture
2. **src/brokers/ibkr/integration.py** - Update to use new client
3. **src/api/routes/portfolio.py** - No changes needed
4. **src/main.py** - Update startup/shutdown handlers

### 4.2 Implementation Steps

#### Step 1: Create Thread-Based Client

```python
# src/brokers/ibkr/client.py
import threading
import queue
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

class IBKRClientThread(threading.Thread):
    """Runs IB API in separate thread."""
    
    def __init__(self, host, port, client_id):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.connected = threading.Event()
        self.running = True
        
    def run(self):
        """Main thread loop."""
        # Create client in this thread
        self.wrapper = IBKRWrapper()
        self.client = EClient(self.wrapper)
        
        # Connect
        self.client.connect(self.host, self.port, self.client_id)
        
        # Run event loop
        while self.running:
            # Process requests
            try:
                request = self.request_queue.get(timeout=0.1)
                self._handle_request(request)
            except queue.Empty:
                pass
            
            # Let ibapi process messages
            time.sleep(0.01)
        
        self.client.disconnect()
    
    def _handle_request(self, request):
        """Handle request from main thread."""
        action = request['action']
        if action == 'get_account':
            # Make ibapi call
            self.client.reqAccountSummary(...)
            # Wait for response
            # Put result in response_queue
```

#### Step 2: Create Async Wrapper

```python
class IBKRBroker:
    """Async wrapper around thread-based client."""
    
    def __init__(self, ...):
        self._thread = None
        
    async def connect(self):
        self._thread = IBKRClientThread(...)
        self._thread.start()
        # Wait for connection
        await asyncio.wait_for(
            self._async_wait_for_connect(),
            timeout=10
        )
    
    async def _async_wait_for_connect(self):
        while not self._thread.connected.is_set():
            await asyncio.sleep(0.1)
    
    async def get_account(self):
        # Send request to thread
        self._thread.request_queue.put({
            'action': 'get_account'
        })
        # Wait for response
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self._thread.response_queue.get
        )
        return response
```

### 4.3 Testing Plan

1. **Unit Test:**
   ```bash
   python test_ib_thread.py
   ```
   - Should connect without errors
   - Should get account info
   - Should disconnect cleanly

2. **Integration Test:**
   ```bash
   python -m cli.main server start
   curl http://localhost:8000/api/portfolio/account
   ```
   - Should return IB account data
   - Should show $250,000 cash

3. **End-to-End Test:**
   - Place paper trade through API
   - Verify in IB Gateway

---

## 5. Timeline Estimate

| Task | Estimated Time |
|------|----------------|
| Implement thread-based client | 2 hours |
| Update integration layer | 30 min |
| Testing and debugging | 1 hour |
| Documentation | 30 min |
| **Total** | **4 hours** |

---

## 6. Immediate Next Steps

1. ✅ Review this plan
2. 🔄 Approve approach (Option A)
3. 🛠️ Implement thread-based client
4. 🧪 Test with IB Gateway
5. 🚀 Deploy and verify

---

## 7. Fallback Options

If Option A proves too complex:

1. **Use Internal Paper Trading Only**
   - TradeMind's $100K paper trading works fine
   - No IB integration needed
   - Can still analyze and generate signals

2. **Use REST API Instead of Socket**
   - IB has Client Portal API
   - HTTP-based, no socket issues
   - Limited functionality but simpler

---

*Plan created: 2026-02-10*
*Status: Ready for implementation*
