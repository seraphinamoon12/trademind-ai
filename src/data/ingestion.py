"""Market data ingestion pipeline."""
from datetime import datetime
from typing import List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from src.core.database import MarketData, get_db
from src.data.providers import yahoo_provider
from src.config import settings


class DataIngestion:
    """Ingest market data from providers to TimescaleDB."""
    
    def __init__(self):
        self.provider = yahoo_provider
    
    def ingest_symbol(
        self, 
        symbol: str, 
        period: str = "2y",
        db: Optional[Session] = None
    ) -> int:
        """Ingest historical data for a symbol."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            # Fetch from Yahoo Finance
            df = self.provider.get_historical(symbol, period=period)
            if df is None or df.empty:
                print(f"No data found for {symbol}")
                return 0
            
            # Prepare records
            records = []
            for _, row in df.iterrows():
                record = MarketData(
                    time=row['date'].to_pydatetime() if hasattr(row['date'], 'to_pydatetime') else pd.to_datetime(row['date']).to_pydatetime(),
                    symbol=symbol.upper(),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['volume']) if pd.notna(row['volume']) else 0
                )
                records.append(record)
            
            # Bulk insert with upsert
            from sqlalchemy.dialects.postgresql import insert
            
            for record in records:
                stmt = insert(MarketData).values(
                    time=record.time,
                    symbol=record.symbol,
                    open=record.open,
                    high=record.high,
                    low=record.low,
                    close=record.close,
                    volume=record.volume
                ).on_conflict_do_nothing()
                db.execute(stmt)
            
            db.commit()
            print(f"Ingested {len(records)} records for {symbol}")
            return len(records)
            
        except Exception as e:
            print(f"Error ingesting {symbol}: {e}")
            db.rollback()
            return 0
        finally:
            if should_close:
                db.close()
    
    def ingest_watchlist(self, symbols: Optional[List[str]] = None) -> dict:
        """Ingest data for all watchlist symbols."""
        symbols = symbols or settings.watchlist
        results = {}
        
        for symbol in symbols:
            count = self.ingest_symbol(symbol)
            results[symbol] = count
        
        return results
    
    def get_stored_data(
        self, 
        symbol: str, 
        days: int = 365,
        db: Optional[Session] = None
    ) -> Optional[pd.DataFrame]:
        """Retrieve stored market data from database."""
        should_close = db is None
        if db is None:
            db = next(get_db())
        
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            records = db.query(MarketData).filter(
                MarketData.symbol == symbol.upper(),
                MarketData.time >= cutoff
            ).order_by(MarketData.time).all()
            
            if not records:
                return None
            
            df = pd.DataFrame([{
                'date': r.time,
                'symbol': r.symbol,
                'open': float(r.open),
                'high': float(r.high),
                'low': float(r.low),
                'close': float(r.close),
                'volume': r.volume
            } for r in records])
            
            return df
            
        except Exception as e:
            print(f"Error retrieving data for {symbol}: {e}")
            return None
        finally:
            if should_close:
                db.close()


# Global ingestion instance
ingestion = DataIngestion()
