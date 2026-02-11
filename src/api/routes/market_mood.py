"""Market Mood API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.core.database import get_db
from src.market_mood.detector import MarketMoodDetector
from src.market_mood.config import MarketMoodConfig
from src.market_mood.backtest import MoodBacktester, run_mood_backtest

router = APIRouter()
logger = logging.getLogger(__name__)

detector = None

def get_detector():
    """Get or create market mood detector instance."""
    global detector
    if detector is None:
        detector = MarketMoodDetector()
    return detector


@router.get("/")
async def get_root():
    """Get API root information."""
    return {
        "name": "Market Mood API",
        "version": "1.0.0",
        "endpoints": [
            "GET /api/market/mood - Current mood snapshot",
            "GET /api/market/mood/history - Historical mood data",
            "GET /api/market/mood/indicators - Individual indicator values",
            "GET /api/market/mood/signals - Trading signals based on mood",
            "POST /api/market/mood/refresh - Force refresh of indicators",
            "GET /api/market/mood/dashboard - Dashboard overview",
            "GET /api/market/mood/alerts - Active alerts",
            "POST /api/market/mood/backtest - Run mood-based backtest",
            "GET /api/market/mood/backtest/results - Get backtest results"
        ]
    }


@router.get("/mood")
async def get_current_mood(db: Session = Depends(get_db)):
    """
    Get current market mood snapshot.

    Returns:
        Current mood data with composite score, sentiment, and confidence
    """
    try:
        detect = get_detector()
        mood = detect.get_current_mood(refresh=False)

        return {
            "mood": mood,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching current mood: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch current mood: {str(e)}"
        )


@router.get("/mood/history")
async def get_mood_history(
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """
    Get historical mood data.

    Args:
        days: Number of days of history to return (1-90)

    Returns:
        Historical mood entries
    """
    try:
        detect = get_detector()
        history = detect.get_mood_history(days=days)

        return {
            "history": history,
            "days": days,
            "count": len(history),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching mood history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch mood history: {str(e)}"
        )


@router.get("/mood/indicators")
async def get_indicator_values(db: Session = Depends(get_db)):
    """
    Get individual indicator values.

    Returns:
        All indicator scores and their details
    """
    try:
        detect = get_detector()
        indicators = detect.get_indicator_scores()

        formatted_indicators = {}
        for name, data in indicators.items():
            if data:
                formatted_indicators[name] = {
                    "score": data.get("score"),
                    "trend": data.get("trend"),
                    "value": data.get("value"),
                    "interpretation": data.get("metadata", {}).get("interpretation"),
                    "timestamp": data.get("timestamp")
                }
            else:
                formatted_indicators[name] = {
                    "score": None,
                    "trend": None,
                    "interpretation": "Data unavailable"
                }

        return {
            "indicators": formatted_indicators,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching indicator values: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch indicator values: {str(e)}"
        )


@router.get("/mood/signals")
async def get_trading_signals(db: Session = Depends(get_db)):
    """
    Get trading signals based on mood.

    Returns:
        Trading signals with recommendations
    """
    try:
        detect = get_detector()
        signals = detect.get_trading_signals(refresh=False)

        return {
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching trading signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trading signals: {str(e)}"
        )


@router.post("/mood/refresh")
async def refresh_indicators(db: Session = Depends(get_db)):
    """
    Force refresh of all market mood indicators.

    Returns:
        Refreshed mood data and indicators
    """
    try:
        detect = get_detector()
        detect.refresh_indicators()

        mood = detect.get_current_mood(refresh=False)
        signals = detect.get_trading_signals(refresh=False)

        return {
            "mood": mood,
            "signals": signals,
            "message": "Indicators refreshed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error refreshing indicators: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh indicators: {str(e)}"
        )


@router.get("/mood/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get dashboard overview with current status.

    Returns:
        Comprehensive dashboard data including mood, signals, indicators
    """
    try:
        detect = get_detector()
        report = detect.get_comprehensive_report()

        status = detect.get_status()

        return {
            "dashboard": {
                "mood": report.get("mood"),
                "signals": report.get("signals"),
                "trend": report.get("trend"),
                "position_sizing": report.get("position_sizing"),
                "risk_adjustments": report.get("risk_adjustments"),
            },
            "status_info": status,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard: {str(e)}"
        )


@router.get("/mood/alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """
    Get active alerts based on market mood conditions.

    Returns:
        Active alerts and warnings
    """
    try:
        detect = get_detector()
        mood = detect.get_current_mood(refresh=False)
        signals = detect.get_trading_signals(refresh=False)

        alerts = []

        composite_score = mood.get("composite_score", 0.0)
        classification = signals.get("mood_classification", "neutral")

        if classification == "extreme_fear":
            alerts.append({
                "severity": "info",
                "type": "market_condition",
                "message": "Market in extreme fear - potential buying opportunity",
                "recommendation": "Consider increasing position sizes by 50%",
                "classification": classification,
                "score": composite_score
            })
        elif classification == "extreme_greed":
            alerts.append({
                "severity": "warning",
                "type": "market_condition",
                "message": "Market in extreme greed - high risk condition",
                "recommendation": "Consider reducing exposure or skipping trades",
                "classification": classification,
                "score": composite_score
            })

        confidence = mood.get("confidence", 0.0)
        if confidence < 0.5:
            alerts.append({
                "severity": "warning",
                "type": "data_quality",
                "message": f"Low confidence in mood data: {confidence:.1%}",
                "recommendation": "Some indicators may be unavailable",
                "classification": classification,
                "score": composite_score
            })

        valid_indicators = mood.get("valid_indicators", [])
        missing_indicators = mood.get("missing_indicators", [])

        if missing_indicators:
            alerts.append({
                "severity": "info",
                "type": "data_availability",
                "message": f"{len(missing_indicators)} indicators unavailable",
                "recommendation": f"Missing: {', '.join(missing_indicators)}",
                "classification": classification,
                "score": composite_score
            })

        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@router.get("/config")
async def get_config(db: Session = Depends(get_db)):
    """
    Get current market mood configuration.

    Returns:
        Current configuration settings
    """
    try:
        config = MarketMoodConfig()

        return {
            "config": {
                "enable_signals": config.enable_signals,
                "signal_confidence_threshold": config.signal_confidence_threshold,
                "trend_lookback_days": config.trend_lookback_days,
                "extreme_fear_threshold": config.extreme_fear_threshold,
                "fear_threshold": config.fear_threshold,
                "greed_threshold": config.greed_threshold,
                "extreme_greed_threshold": config.extreme_greed_threshold,
                "indicator_weights": config.get_indicator_weights(),
                "cache_settings": {
                    "vix": config.vix_cache_ttl,
                    "breadth": config.breadth_cache_ttl,
                    "put_call": config.put_call_cache_ttl,
                    "ma_trends": config.ma_trends_cache_ttl,
                    "fear_greed": config.fear_greed_cache_ttl,
                    "dxy": config.dxy_cache_ttl,
                    "credit_spreads": config.credit_spreads_cache_ttl,
                    "yield_curve": config.yield_curve_cache_ttl,
                }
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch config: {str(e)}"
        )


@router.post("/mood/backtest")
async def run_mood_backtest(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    symbol: str = Query("SPY", description="Symbol to backtest"),
    initial_capital: float = Query(100000, ge=1000, description="Initial capital"),
    db: Session = Depends(get_db)
):
    """
    Run a mood-based backtest.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        symbol: Trading symbol (default: SPY)
        initial_capital: Initial capital for backtest (default: 100000)

    Returns:
        Backtest results with performance metrics
    """
    try:
        backtester = MoodBacktester(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            symbol=symbol.upper(),
        )

        result = backtester.run_backtest()

        return {
            "status": "success",
            "backtest_summary": {
                "symbol": result.start_date,
                "start_date": result.start_date.isoformat() if result.start_date else None,
                "end_date": result.end_date.isoformat() if result.end_date else None,
                "initial_capital": result.initial_capital,
                "final_capital": result.final_capital,
                "total_trades": len(result.trades),
            },
            "performance_metrics": result.metrics,
            "buy_and_hold": {
                "return": result.buy_and_hold_return,
                "return_pct": result.buy_and_hold_return * 100,
            },
            "signals_by_mood": backtester._analyze_signals_by_mood(),
            "trades_by_mood": backtester._analyze_trades_by_mood(),
            "trades_count": len(result.trades),
            "signals_count": len(result.signals),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backtest: {str(e)}"
        )


@router.post("/mood/backtest/export")
async def export_mood_backtest(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    symbol: str = Query("SPY", description="Symbol to backtest"),
    initial_capital: float = Query(100000, ge=1000, description="Initial capital"),
    output_dir: str = Query("backtest_results", description="Output directory"),
    db: Session = Depends(get_db)
):
    """
    Run a mood-based backtest and export results to files.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        symbol: Trading symbol (default: SPY)
        initial_capital: Initial capital for backtest (default: 100000)
        output_dir: Directory to save output files (default: backtest_results)

    Returns:
        Dictionary with file paths to exported results
    """
    try:
        backtester = MoodBacktester(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            symbol=symbol.upper(),
        )

        backtester.run_backtest()
        files = backtester.export_results(output_dir=output_dir)

        return {
            "status": "success",
            "message": "Backtest completed and results exported",
            "files": files,
            "trades_count": len(backtester.trades),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backtest: {str(e)}"
        )


@router.get("/mood/backtest/report")
async def get_backtest_report(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    symbol: str = Query("SPY", description="Symbol to backtest"),
    initial_capital: float = Query(100000, ge=1000, description="Initial capital"),
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive backtest report.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        symbol: Trading symbol (default: SPY)
        initial_capital: Initial capital for backtest (default: 100000)

    Returns:
        Comprehensive backtest report
    """
    try:
        backtester = MoodBacktester(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            symbol=symbol.upper(),
        )

        backtester.run_backtest()
        report = backtester.generate_report()

        return {
            "status": "success",
            "report": report,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )
