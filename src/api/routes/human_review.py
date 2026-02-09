"""Human-in-the-loop approval system with WebSocket support."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

# Track connections by symbol for room-based support
symbol_connections: Dict[str, Set[WebSocket]] = {}

# Track connection timestamps for rate limiting
connection_times: Dict[WebSocket, float] = {}
RATE_LIMIT_SECONDS = 1

# Store pending approvals
pending_approvals: Dict[str, Dict] = {}


def validate_token(token: Optional[str]) -> bool:
    """Validate WebSocket authentication token."""
    valid_token = settings.websocket_auth_token
    if not valid_token:
        return True
    if not token:
        return False
    return token == valid_token


class TradeApprovalRequest(BaseModel):
    """Request for trade approval."""
    trade_id: str
    approved: bool
    feedback: str = ""


class TradeInfo(BaseModel):
    """Trade information for human review."""
    id: str
    symbol: str
    action: str
    confidence: float
    reasoning: str
    timestamp: str
    technical_signals: Dict[str, Any] = {}
    sentiment_signals: Dict[str, Any] = {}
    debate_result: Dict[str, Any] = {}


@router.websocket("/ws/trades")
async def websocket_trades_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not validate_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return
    """WebSocket for real-time trade notifications."""
    await websocket.accept()
    active_connections.add(websocket)
    connection_times[websocket] = time.time()

    try:
        logger.info(f"WebSocket connection established (total: {len(active_connections)})")

        while True:
            now = time.time()
            last_message = connection_times.get(websocket, 0)
            if now - last_message < RATE_LIMIT_SECONDS:
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded. Please slow down."
                })
                await asyncio.sleep(RATE_LIMIT_SECONDS - (now - last_message))
                continue

            connection_times[websocket] = now

            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                if message.get("action") == "approve":
                    trade_id = message.get("trade_id")
                    feedback = message.get("feedback", "")
                    await process_approval(trade_id, approved=True, feedback=feedback)

                elif message.get("action") == "reject":
                    trade_id = message.get("trade_id")
                    feedback = message.get("feedback", "")
                    await process_approval(trade_id, approved=False, feedback=feedback)

                elif message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from WebSocket: {data}")
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected")
        active_connections.discard(websocket)
        connection_times.pop(websocket, None)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)
        connection_times.pop(websocket, None)


@router.websocket("/ws/trades/{symbol}")
async def websocket_symbol_endpoint(websocket: WebSocket, symbol: str, token: Optional[str] = Query(None)):
    if not validate_token(token):
        await websocket.close(code=4001, reason="Invalid token")
        return

    if not symbol or len(symbol) > 5:
        await websocket.close(code=4000, reason="Invalid symbol")
        return
    """Room-based WebSocket for specific symbol trades."""
    if not symbol or len(symbol) > 5:
        await websocket.close(code=4000, reason="Invalid symbol")
        return

    await websocket.accept()

    if symbol not in symbol_connections:
        symbol_connections[symbol] = set()
    symbol_connections[symbol].add(websocket)
    active_connections.add(websocket)
    connection_times[websocket] = time.time()

    try:
        logger.info(f"WebSocket connection established for {symbol} (total: {len(active_connections)})")

        while True:
            now = time.time()
            last_message = connection_times.get(websocket, 0)
            if now - last_message < RATE_LIMIT_SECONDS:
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded. Please slow down."
                })
                await asyncio.sleep(RATE_LIMIT_SECONDS - (now - last_message))
                continue

            connection_times[websocket] = now

            data = await websocket.receive_text()
            try:
                message = json.loads(data)

                if message.get("action") == "approve":
                    trade_id = message.get("trade_id")
                    feedback = message.get("feedback", "")
                    await process_approval(trade_id, approved=True, feedback=feedback)
                    await broadcast_to_symbol_room(symbol, {
                        "type": "trade_decision",
                        "trade_id": trade_id,
                        "approved": True,
                        "feedback": feedback
                    }, exclude=websocket)

                elif message.get("action") == "reject":
                    trade_id = message.get("trade_id")
                    feedback = message.get("feedback", "")
                    await process_approval(trade_id, approved=False, feedback=feedback)
                    await broadcast_to_symbol_room(symbol, {
                        "type": "trade_decision",
                        "trade_id": trade_id,
                        "approved": False,
                        "feedback": feedback
                    }, exclude=websocket)

                elif message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    await broadcast_to_symbol_room(symbol, message, exclude=websocket)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from WebSocket: {data}")
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection disconnected for {symbol}")
        active_connections.discard(websocket)
        connection_times.pop(websocket, None)
        if symbol in symbol_connections:
            symbol_connections[symbol].discard(websocket)
            if not symbol_connections[symbol]:
                del symbol_connections[symbol]
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
        active_connections.discard(websocket)
        connection_times.pop(websocket, None)
        if symbol in symbol_connections:
            symbol_connections[symbol].discard(websocket)


async def broadcast_to_symbol_room(symbol: str, message: dict, exclude: Optional[WebSocket] = None):
    """Broadcast message to all connections for a specific symbol."""
    if symbol not in symbol_connections:
        return

    disconnected = set()
    for conn in symbol_connections[symbol]:
        if conn == exclude:
            continue
        try:
            await conn.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.add(conn)

    for conn in disconnected:
        symbol_connections[symbol].discard(conn)
        active_connections.discard(conn)


async def notify_new_trade(trade_info: Dict):
    """Send trade notification to all connected clients."""
    message = {
        "type": "new_trade",
        "data": trade_info
    }
    
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.add(connection)
    
    # Clean up disconnected clients
    active_connections.difference_update(disconnected)


async def process_approval(trade_id: str, approved: bool, feedback: str):
    """Process trade approval/rejection."""
    if trade_id in pending_approvals:
        pending_approvals[trade_id]["approved"] = approved
        pending_approvals[trade_id]["status"] = "approved" if approved else "rejected"
        pending_approvals[trade_id]["feedback"] = feedback
        
        # Notify all clients of decision
        message = {
            "type": "trade_decision",
            "trade_id": trade_id,
            "approved": approved,
            "feedback": feedback
        }
        
        disconnected = set()
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        active_connections.difference_update(disconnected)
        
        logger.info(
            f"Trade {trade_id} {'approved' if approved else 'rejected'}: {feedback}"
        )
    else:
        logger.warning(f"Trade {trade_id} not found in pending approvals")


async def create_trade_approval_request(
    symbol: str,
    action: str,
    confidence: float,
    reasoning: str,
    technical_signals: Optional[Dict] = None,
    sentiment_signals: Optional[Dict] = None,
    debate_result: Optional[Dict] = None
) -> str:
    """
    Create a trade approval request and notify via WebSocket.
    
    Args:
        symbol: Stock symbol
        action: Trading action (BUY/SELL/HOLD)
        confidence: Confidence score 0-1
        reasoning: Trading reasoning
        technical_signals: Technical analysis signals
        sentiment_signals: Sentiment analysis signals
        debate_result: Debate result (if applicable)
        
    Returns:
        trade_id: ID of the created trade approval request
    """
    trade_id = str(uuid.uuid4())
    
    trade_info = {
        "id": trade_id,
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technical_signals": technical_signals or {},
        "sentiment_signals": sentiment_signals or {},
        "debate_result": debate_result or {}
    }
    
    # Add to pending approvals
    pending_approvals[trade_id] = trade_info
    
    # Notify via WebSocket
    await notify_new_trade(trade_info)
    
    logger.info(f"Created trade approval request {trade_id} for {symbol} {action}")
    
    return trade_id


async def await_trade_approval(
    trade_id: str,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Wait for human approval of a trade.
    
    Args:
        trade_id: ID of the trade approval request
        timeout: Timeout in seconds (default: 5 minutes)
        
    Returns:
        Dict with approved (bool) and feedback (str)
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if trade_id in pending_approvals:
            trade = pending_approvals[trade_id]
            if trade.get("status") in ["approved", "rejected"]:
                approved = trade.get("approved", False)
                feedback = trade.get("feedback", "")
                
                # Clean up after approval/rejection
                del pending_approvals[trade_id]
                
                return {
                    "approved": approved,
                    "feedback": feedback
                }
        
        await asyncio.sleep(1)
    
    # Timeout - default to rejection
    logger.warning(f"Human review timeout for trade {trade_id}")
    
    if trade_id in pending_approvals:
        del pending_approvals[trade_id]
    
    return {
        "approved": False,
        "feedback": "Timeout - trade rejected"
    }


@router.get("/human-review", response_class=HTMLResponse)
async def human_review_page():
    """Serve the human review HTML page."""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Trade Review Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
            margin: 0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333;
            margin-top: 0;
        }
        .trade-card { 
            border: 1px solid #e0e0e0; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 8px;
            background-color: #fafafa;
        }
        .buy { border-left: 5px solid #4CAF50; }
        .sell { border-left: 5px solid #f44336; }
        .hold { border-left: 5px solid #FF9800; }
        .trade-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .trade-symbol {
            font-size: 1.5em;
            font-weight: bold;
        }
        .trade-action {
            padding: 5px 15px;
            border-radius: 4px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .buy .trade-action { background-color: #4CAF50; color: white; }
        .sell .trade-action { background-color: #f44336; color: white; }
        .hold .trade-action { background-color: #FF9800; color: white; }
        .trade-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .detail-item {
            padding: 10px;
            background-color: white;
            border-radius: 4px;
        }
        .detail-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        .detail-value {
            font-weight: 500;
            color: #333;
        }
        .confidence-high { color: #4CAF50; }
        .confidence-medium { color: #FF9800; }
        .confidence-low { color: #f44336; }
        .reasoning {
            padding: 15px;
            background-color: white;
            border-radius: 4px;
            margin-bottom: 15px;
            color: #555;
            line-height: 1.6;
        }
        .buttons {
            display: flex;
            gap: 10px;
        }
        button { 
            padding: 12px 24px; 
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.2s;
        }
        .approve { 
            background-color: #4CAF50; 
            color: white;
        }
        .approve:hover { background-color: #45a049; }
        .reject { 
            background-color: #f44336; 
            color: white;
        }
        .reject:hover { background-color: #da190b; }
        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 4px;
            font-weight: 500;
        }
        .status-approved { background-color: #e8f5e9; color: #2e7d32; }
        .status-rejected { background-color: #ffebee; color: #c62828; }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .timestamp {
            color: #666;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Trade Review Dashboard</h1>
        <div id="trades"></div>
        <div id="empty-state" class="empty-state">
            Waiting for trades requiring review...
        </div>
    </div>
    
    <script>
        let ws = null;
        const trades = new Map();
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/trades`);
            
            ws.onopen = function(event) {
                console.log('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const msg = JSON.parse(event.data);
                if (msg.type === 'new_trade') {
                    addTrade(msg.data);
                } else if (msg.type === 'trade_decision') {
                    updateTradeDecision(msg.trade_id, msg.approved, msg.feedback);
                } else if (msg.type === 'pong') {
                    // Heartbeat response
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket disconnected, reconnecting in 3s...');
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function addTrade(trade) {
            if (trades.has(trade.id)) return; // Already exists
            
            trades.set(trade.id, trade);
            
            const div = document.createElement('div');
            div.className = `trade-card ${trade.action.toLowerCase()}`;
            div.id = `trade-${trade.id}`;
            
            const confidenceClass = trade.confidence >= 0.7 ? 'confidence-high' : 
                                  trade.confidence >= 0.5 ? 'confidence-medium' : 
                                  'confidence-low';
            
            div.innerHTML = `
                <div class="trade-header">
                    <div class="trade-symbol">${trade.symbol}</div>
                    <div class="trade-action">${trade.action}</div>
                </div>
                <div class="trade-details">
                    <div class="detail-item">
                        <div class="detail-label">Confidence</div>
                        <div class="detail-value ${confidenceClass}">${(trade.confidence * 100).toFixed(1)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Timestamp</div>
                        <div class="detail-value timestamp">${new Date(trade.timestamp).toLocaleString()}</div>
                    </div>
                </div>
                <div class="reasoning">
                    <strong>Reasoning:</strong> ${trade.reasoning}
                </div>
                <div class="buttons">
                    <button class="approve" onclick="approve('${trade.id}')">✓ Approve</button>
                    <button class="reject" onclick="reject('${trade.id}')">✗ Reject</button>
                </div>
                <div id="status-${trade.id}" class="status" style="display: none;"></div>
            `;
            
            const tradesDiv = document.getElementById('trades');
            tradesDiv.insertBefore(div, tradesDiv.firstChild);
            
            document.getElementById('empty-state').style.display = 'none';
        }
        
        function updateTradeDecision(tradeId, approved, feedback) {
            const statusDiv = document.getElementById(`status-${tradeId}`);
            const buttonsDiv = statusDiv.previousElementSibling;
            
            if (statusDiv && buttonsDiv) {
                buttonsDiv.style.display = 'none';
                statusDiv.style.display = 'block';
                statusDiv.className = `status status-${approved ? 'approved' : 'rejected'}`;
                statusDiv.textContent = `${approved ? '✓ Approved' : '✗ Rejected'}${feedback ? ': ' + feedback : ''}`;
            }
        }
        
        function approve(tradeId) {
            ws.send(JSON.stringify({action: 'approve', trade_id: tradeId}));
        }
        
        function reject(tradeId) {
            ws.send(JSON.stringify({action: 'reject', trade_id: tradeId}));
        }
        
        // Connect on page load
        connectWebSocket();
        
        // Send heartbeat every 30s
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'ping'}));
            }
        }, 30000);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.get("/api/human-review/pending")
async def list_pending_approvals():
    """List all pending trade approvals."""
    return {
        "pending": list(pending_approvals.values()),
        "count": len(pending_approvals)
    }


@router.post("/api/human-review/approve")
async def manual_approve(request: TradeApprovalRequest):
    """Manually approve or reject a trade (alternative to WebSocket)."""
    if not request.trade_id or len(request.trade_id) < 10:
        raise HTTPException(status_code=400, detail="Invalid trade_id")

    if request.trade_id not in pending_approvals:
        raise HTTPException(status_code=404, detail="Trade not found")

    await process_approval(request.trade_id, request.approved, request.feedback)

    return {
        "trade_id": request.trade_id,
        "status": "approved" if request.approved else "rejected",
        "feedback": request.feedback
    }
