"""Market data fetching using yfinance."""

from dataclasses import dataclass
from typing import Optional
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


@dataclass
class SymbolData:
    """Data for a single symbol."""
    symbol: str
    current_price: float
    previous_close: float
    intraday_change_pct: float
    change_5d_pct: Optional[float]
    high_52w: Optional[float]
    low_52w: Optional[float]
    sma_200: Optional[float]
    name: str


@dataclass
class MarketSnapshot:
    """Complete market snapshot with all tracked symbols."""
    timestamp: datetime
    data: dict[str, SymbolData]

    def get(self, symbol: str) -> Optional[SymbolData]:
        """Get data for a specific symbol."""
        return self.data.get(symbol)


# Symbol mappings
SYMBOLS = {
    'SPY': 'S&P 500 ETF',
    'QQQ': 'Nasdaq-100 ETF',
    'IWM': 'Russell 2000 ETF',
    '^TNX': '10-Year Treasury Yield',
    'TLT': '20+ Year Treasury ETF',
    'HYG': 'High Yield Corp Bond ETF',
    '^VIX': 'Volatility Index',
    'DX-Y.NYB': 'US Dollar Index',
    'GLD': 'Gold ETF',
    'BTC-USD': 'Bitcoin',
}


def fetch_symbol_data(symbol: str, name: str) -> Optional[SymbolData]:
    """Fetch data for a single symbol."""
    try:
        ticker = yf.Ticker(symbol)

        # Get historical data for calculations
        hist = ticker.history(period='1y')
        if hist.empty:
            return None

        current_price = hist['Close'].iloc[-1]

        # Previous close (day before last)
        if len(hist) >= 2:
            previous_close = hist['Close'].iloc[-2]
        else:
            previous_close = current_price

        # Intraday change
        intraday_change_pct = ((current_price - previous_close) / previous_close) * 100

        # 5-day return
        if len(hist) >= 6:
            price_5d_ago = hist['Close'].iloc[-6]
            change_5d_pct = ((current_price - price_5d_ago) / price_5d_ago) * 100
        else:
            change_5d_pct = None

        # 52-week high/low
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()

        # 200-day SMA
        if len(hist) >= 200:
            sma_200 = hist['Close'].tail(200).mean()
        else:
            sma_200 = None

        return SymbolData(
            symbol=symbol,
            current_price=current_price,
            previous_close=previous_close,
            intraday_change_pct=intraday_change_pct,
            change_5d_pct=change_5d_pct,
            high_52w=high_52w,
            low_52w=low_52w,
            sma_200=sma_200,
            name=name,
        )
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def fetch_market_snapshot() -> MarketSnapshot:
    """Fetch complete market snapshot for all tracked symbols."""
    data = {}

    for symbol, name in SYMBOLS.items():
        symbol_data = fetch_symbol_data(symbol, name)
        if symbol_data:
            data[symbol] = symbol_data

    return MarketSnapshot(
        timestamp=datetime.now(),
        data=data,
    )


def get_vix_previous_close() -> Optional[float]:
    """Get VIX previous close for spike detection."""
    try:
        ticker = yf.Ticker('^VIX')
        hist = ticker.history(period='5d')
        if len(hist) >= 2:
            return hist['Close'].iloc[-2]
        return None
    except Exception:
        return None
