"""Calculated market indicators and metrics."""

from typing import Optional
from src.data import MarketSnapshot, SymbolData


def get_drawdown_from_high(symbol_data: SymbolData) -> Optional[float]:
    """Calculate drawdown from 52-week high as percentage."""
    if symbol_data.high_52w is None or symbol_data.high_52w == 0:
        return None
    return ((symbol_data.current_price - symbol_data.high_52w) / symbol_data.high_52w) * 100


def get_5d_return(symbol_data: SymbolData) -> Optional[float]:
    """Get 5-day return percentage."""
    return symbol_data.change_5d_pct


def get_intraday_change(symbol_data: SymbolData) -> float:
    """Get intraday change percentage."""
    return symbol_data.intraday_change_pct


def is_below_200dma(symbol_data: SymbolData) -> bool:
    """Check if price is below 200-day moving average."""
    if symbol_data.sma_200 is None:
        return False
    return symbol_data.current_price < symbol_data.sma_200


def get_yield_change_bps(snapshot: MarketSnapshot) -> Optional[float]:
    """Get 10Y yield daily change in basis points."""
    tnx = snapshot.get('^TNX')
    if tnx is None:
        return None
    # TNX is quoted in percentage points, so 1-day change * 100 = bps
    return tnx.intraday_change_pct * 10  # Approximate conversion


def get_spread_indicator(snapshot: MarketSnapshot) -> Optional[float]:
    """
    Get credit spread indicator based on HYG vs TLT relative performance.
    Negative = spreads widening (risk-off)
    """
    hyg = snapshot.get('HYG')
    tlt = snapshot.get('TLT')

    if hyg is None or tlt is None:
        return None

    # If HYG underperforming TLT significantly, spreads are widening
    return hyg.intraday_change_pct - tlt.intraday_change_pct


def get_risk_appetite_score(snapshot: MarketSnapshot) -> dict:
    """
    Calculate risk appetite indicators.
    Returns dict with various risk sentiment metrics.
    """
    metrics = {}

    # Equity risk appetite: QQQ vs SPY (growth vs broad market)
    qqq = snapshot.get('QQQ')
    spy = snapshot.get('SPY')
    if qqq and spy:
        metrics['growth_vs_broad'] = qqq.intraday_change_pct - spy.intraday_change_pct

    # Small cap vs large cap: IWM vs SPY
    iwm = snapshot.get('IWM')
    if iwm and spy:
        metrics['smallcap_vs_large'] = iwm.intraday_change_pct - spy.intraday_change_pct

    # Safe haven demand: GLD performance
    gld = snapshot.get('GLD')
    if gld:
        metrics['gold_bid'] = gld.intraday_change_pct

    # Dollar strength (inverse risk appetite)
    dxy = snapshot.get('DX-Y.NYB')
    if dxy:
        metrics['dollar_strength'] = dxy.intraday_change_pct

    return metrics


def format_pct(value: Optional[float], decimals: int = 2) -> str:
    """Format percentage value for display."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_price(value: float, symbol: str = "") -> str:
    """Format price for display based on symbol type."""
    if symbol in ['^TNX']:
        return f"{value:.2f}%"  # Yield
    elif symbol in ['^VIX']:
        return f"{value:.2f}"  # Index level
    elif symbol in ['BTC-USD']:
        return f"${value:,.0f}"  # Crypto
    else:
        return f"${value:.2f}"  # Standard price
