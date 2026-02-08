"""Technical indicators using pandas-ta."""
from typing import Optional
import pandas as pd
import pandas_ta as ta


class TechnicalIndicators:
    """Calculate technical indicators for price data."""
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to dataframe."""
        df = df.copy()
        
        # Ensure required columns exist
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df['macd'] = macd.get('MACD_12_26_9')
            df['macd_signal'] = macd.get('MACDs_12_26_9')
            df['macd_hist'] = macd.get('MACDh_12_26_9')
        
        # Moving Averages
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['sma_200'] = ta.sma(df['close'], length=200)
        df['ema_12'] = ta.ema(df['close'], length=12)
        df['ema_26'] = ta.ema(df['close'], length=26)
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            # Find BB columns (they may have variable naming)
            bb_cols = bb.columns.tolist()
            upper_col = [c for c in bb_cols if 'BBU' in c][0] if any('BBU' in c for c in bb_cols) else None
            lower_col = [c for c in bb_cols if 'BBL' in c][0] if any('BBL' in c for c in bb_cols) else None
            mid_col = [c for c in bb_cols if 'BBM' in c][0] if any('BBM' in c for c in bb_cols) else None
            pct_col = [c for c in bb_cols if 'BBP' in c][0] if any('BBP' in c for c in bb_cols) else None
            
            df['bb_upper'] = bb[upper_col] if upper_col else None
            df['bb_lower'] = bb[lower_col] if lower_col else None
            df['bb_middle'] = bb[mid_col] if mid_col else None
            df['bb_pct'] = bb[pct_col] if pct_col else None
        
        # ATR (Average True Range)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Stochastic
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None:
            df['stoch_k'] = stoch.get('STOCHk_14_3_3')
            df['stoch_d'] = stoch.get('STOCHd_14_3_3')
        
        # OBV (On Balance Volume)
        df['obv'] = ta.obv(df['close'], df['volume'])
        
        return df
    
    @staticmethod
    def get_latest_signals(df: pd.DataFrame) -> dict:
        """Get latest indicator values and signals."""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        signals = {
            'rsi': latest.get('rsi'),
            'macd': latest.get('macd'),
            'macd_signal': latest.get('macd_signal'),
            'sma_50': latest.get('sma_50'),
            'sma_200': latest.get('sma_200'),
            'bb_upper': latest.get('bb_upper'),
            'bb_lower': latest.get('bb_lower'),
            'atr': latest.get('atr'),
        }
        
        # Determine signals
        signals['rsi_signal'] = TechnicalIndicators._rsi_signal(latest.get('rsi'))
        signals['ma_signal'] = TechnicalIndicators._ma_signal(
            latest.get('sma_50'), latest.get('sma_200')
        )
        signals['macd_signal'] = TechnicalIndicators._macd_signal(
            latest.get('macd'), latest.get('macd_signal')
        )
        signals['bb_signal'] = TechnicalIndicators._bb_signal(
            latest.get('close'), latest.get('bb_upper'), latest.get('bb_lower')
        )
        
        return signals
    
    @staticmethod
    def _rsi_signal(rsi: Optional[float]) -> str:
        """RSI-based signal."""
        if rsi is None:
            return "NEUTRAL"
        if rsi < 30:
            return "OVERSOLD"
        elif rsi > 70:
            return "OVERBOUGHT"
        return "NEUTRAL"
    
    @staticmethod
    def _ma_signal(sma_50: Optional[float], sma_200: Optional[float]) -> str:
        """Moving average crossover signal."""
        if sma_50 is None or sma_200 is None:
            return "NEUTRAL"
        if sma_50 > sma_200:
            return "BULLISH"
        return "BEARISH"
    
    @staticmethod
    def _macd_signal(macd: Optional[float], signal: Optional[float]) -> str:
        """MACD signal."""
        if macd is None or signal is None:
            return "NEUTRAL"
        if macd > signal:
            return "BULLISH"
        return "BEARISH"
    
    @staticmethod
    def _bb_signal(close: float, upper: Optional[float], lower: Optional[float]) -> str:
        """Bollinger Bands signal."""
        if upper is None or lower is None:
            return "NEUTRAL"
        if close <= lower:
            return "OVERSOLD"
        elif close >= upper:
            return "OVERBOUGHT"
        return "NEUTRAL"
