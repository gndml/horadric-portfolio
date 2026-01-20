"""Market regime assessment (NORMAL vs DEFENSIVE)."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from src.data import MarketSnapshot, get_vix_previous_close
from src.indicators import is_below_200dma


class Regime(Enum):
    """Market regime classification."""
    NORMAL = "NORMAL"
    DEFENSIVE = "DEFENSIVE"


@dataclass
class RegimeAssessment:
    """Result of regime assessment with reasoning."""
    regime: Regime
    triggers: list[str]
    summary: str


def load_regime_thresholds() -> dict:
    """Load regime thresholds from config."""
    import os
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('regime', {})
    except ImportError:
        pass
    except Exception:
        pass

    # Defaults
    return {
        'hyg_5d_threshold': -3.0,
        'dxy_5d_threshold': 2.0,
        'vix_level_threshold': 30,
        'spy_tlt_combined_threshold': -2.5,
    }


def assess_regime(snapshot: MarketSnapshot) -> RegimeAssessment:
    """
    Assess current market regime.

    DEFENSIVE triggers (any one):
    - HYG 5d return <= -3.0%
    - DXY 5d return >= +2.0%
    - VIX >= 30 AND rising (today > yesterday)
    - SPY <= -2.5% AND TLT < 0 same day
    - (Optional) SPY < 200dma AND rates rising
    """
    thresholds = load_regime_thresholds()
    triggers = []

    # Check HYG 5d stress
    hyg = snapshot.get('HYG')
    if hyg and hyg.change_5d_pct is not None:
        hyg_threshold = thresholds.get('hyg_5d_threshold', -3.0)
        if hyg.change_5d_pct <= hyg_threshold:
            triggers.append(f"Credit stress: HYG 5D return {hyg.change_5d_pct:.1f}%")

    # Check DXY 5d strength
    dxy = snapshot.get('DX-Y.NYB')
    if dxy and dxy.change_5d_pct is not None:
        dxy_threshold = thresholds.get('dxy_5d_threshold', 2.0)
        if dxy.change_5d_pct >= dxy_threshold:
            triggers.append(f"Liquidity tightening: DXY 5D return +{dxy.change_5d_pct:.1f}%")

    # Check VIX elevated AND rising
    vix = snapshot.get('^VIX')
    if vix:
        vix_threshold = thresholds.get('vix_level_threshold', 30)
        if vix.current_price >= vix_threshold:
            vix_prev = get_vix_previous_close()
            if vix_prev is not None and vix.current_price > vix_prev:
                triggers.append(f"Elevated and rising volatility: VIX {vix.current_price:.1f} (prev: {vix_prev:.1f})")
            elif vix_prev is None:
                triggers.append(f"Elevated volatility: VIX {vix.current_price:.1f}")

    # Check combined SPY + TLT stress
    spy = snapshot.get('SPY')
    tlt = snapshot.get('TLT')
    if spy and tlt:
        spy_threshold = thresholds.get('spy_tlt_combined_threshold', -2.5)
        if spy.intraday_change_pct <= spy_threshold and tlt.intraday_change_pct < 0:
            triggers.append(f"Combined stress: SPY {spy.intraday_change_pct:.1f}% and TLT {tlt.intraday_change_pct:.1f}%")

    # Check structural weakness (SPY below 200dma with rates rising)
    if spy and is_below_200dma(spy):
        tnx = snapshot.get('^TNX')
        if tnx and tnx.intraday_change_pct > 0:
            triggers.append(f"Structural weakness: SPY below 200dma with rates rising")

    # Determine regime
    if triggers:
        regime = Regime.DEFENSIVE
        summary = f"DEFENSIVE regime - {len(triggers)} warning signal(s) active"
    else:
        regime = Regime.NORMAL
        summary = "NORMAL regime - no significant stress signals detected"

    return RegimeAssessment(
        regime=regime,
        triggers=triggers,
        summary=summary,
    )


def get_regime_emoji(regime: Regime) -> str:
    """Get emoji for regime display."""
    return "🟢" if regime == Regime.NORMAL else "🔴"


def get_regime_action_guidance(regime: Regime) -> str:
    """Get action guidance based on regime."""
    if regime == Regime.NORMAL:
        return "Standard operations - follow normal position sizing rules"
    else:
        return "Defensive posture - reduce risk, tighten stops, avoid new longs"
