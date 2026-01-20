"""Rule registry with severity levels and cooldowns."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from src.data import MarketSnapshot
from src.indicators import (
    get_drawdown_from_high,
    get_5d_return,
    get_intraday_change,
    is_below_200dma,
    get_spread_indicator,
)


class Severity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Rule:
    """Definition of an alert rule."""
    name: str
    severity: Severity
    category: str
    description: str
    check: Callable[[MarketSnapshot, dict], bool]
    message_template: str


@dataclass
class TriggeredRule:
    """A rule that has been triggered with context."""
    rule: Rule
    value: Optional[float] = None
    symbol: Optional[str] = None
    extra_context: Optional[dict] = None


def load_config() -> dict:
    """Load configuration from config.yml or use defaults."""
    import os
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
    except ImportError:
        pass
    except Exception as e:
        print(f"Warning: Could not load config.yml: {e}")

    # Return defaults
    return {
        'rules': {
            'credit_stress_intraday': -1.5,
            'credit_stress_5d': -3.0,
            'liquidity_stress_intraday': 1.0,
            'liquidity_stress_5d': 2.0,
            'volatility_level': 30,
            'volatility_spike': 8,
            'spy_drawdown_levels': [-2, -4, -6, -10, -15, -20],
            'growth_weakness_threshold': -1.5,
            'smallcap_weakness_threshold': -2.0,
            'defensive_hedge_bid': 1.5,
            'rate_shock_bps': 15,
        },
        'cooldowns': {
            'critical': 45,
            'high': 90,
            'medium': 240,
            'low': 1440,
        }
    }


# Global config - loaded once
_config = None


def get_config() -> dict:
    """Get or load config."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_threshold(key: str, default: float) -> float:
    """Get a threshold value from config."""
    config = get_config()
    rules = config.get('rules', {})
    return rules.get(key, default)


def get_cooldown_minutes(severity: Severity) -> int:
    """Get cooldown duration in minutes for a severity level."""
    config = get_config()
    cooldowns = config.get('cooldowns', {})
    defaults = {'critical': 45, 'high': 90, 'medium': 240, 'low': 1440}
    return cooldowns.get(severity.value, defaults.get(severity.value, 60))


# Rule definitions
def check_credit_stress_intraday(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for intraday credit stress via HYG."""
    hyg = snapshot.get('HYG')
    if hyg is None:
        return False
    threshold = get_threshold('credit_stress_intraday', -1.5)
    triggered = hyg.intraday_change_pct <= threshold
    if triggered:
        ctx['value'] = hyg.intraday_change_pct
        ctx['symbol'] = 'HYG'
    return triggered


def check_credit_stress_5d(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for 5-day credit stress via HYG."""
    hyg = snapshot.get('HYG')
    if hyg is None or hyg.change_5d_pct is None:
        return False
    threshold = get_threshold('credit_stress_5d', -3.0)
    triggered = hyg.change_5d_pct <= threshold
    if triggered:
        ctx['value'] = hyg.change_5d_pct
        ctx['symbol'] = 'HYG'
    return triggered


def check_liquidity_stress_intraday(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for intraday liquidity stress via DXY spike."""
    dxy = snapshot.get('DX-Y.NYB')
    if dxy is None:
        return False
    threshold = get_threshold('liquidity_stress_intraday', 1.0)
    triggered = dxy.intraday_change_pct >= threshold
    if triggered:
        ctx['value'] = dxy.intraday_change_pct
        ctx['symbol'] = 'DXY'
    return triggered


def check_liquidity_stress_5d(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for 5-day liquidity stress via DXY."""
    dxy = snapshot.get('DX-Y.NYB')
    if dxy is None or dxy.change_5d_pct is None:
        return False
    threshold = get_threshold('liquidity_stress_5d', 2.0)
    triggered = dxy.change_5d_pct >= threshold
    if triggered:
        ctx['value'] = dxy.change_5d_pct
        ctx['symbol'] = 'DXY'
    return triggered


def check_volatility_elevated(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check if VIX is at elevated levels."""
    vix = snapshot.get('^VIX')
    if vix is None:
        return False
    threshold = get_threshold('volatility_level', 30)
    triggered = vix.current_price >= threshold
    if triggered:
        ctx['value'] = vix.current_price
        ctx['symbol'] = 'VIX'
    return triggered


def check_volatility_spike(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for VIX spike (large intraday move)."""
    vix = snapshot.get('^VIX')
    if vix is None:
        return False
    threshold = get_threshold('volatility_spike', 8)
    triggered = vix.intraday_change_pct >= threshold
    if triggered:
        ctx['value'] = vix.intraday_change_pct
        ctx['symbol'] = 'VIX'
    return triggered


def check_growth_weakness(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for growth/tech weakness (QQQ underperforming SPY)."""
    qqq = snapshot.get('QQQ')
    spy = snapshot.get('SPY')
    if qqq is None or spy is None:
        return False
    threshold = get_threshold('growth_weakness_threshold', -1.5)
    relative_perf = qqq.intraday_change_pct - spy.intraday_change_pct
    triggered = relative_perf <= threshold
    if triggered:
        ctx['value'] = relative_perf
        ctx['extra'] = {'qqq': qqq.intraday_change_pct, 'spy': spy.intraday_change_pct}
    return triggered


def check_smallcap_weakness(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for small cap weakness (IWM underperforming SPY)."""
    iwm = snapshot.get('IWM')
    spy = snapshot.get('SPY')
    if iwm is None or spy is None:
        return False
    threshold = get_threshold('smallcap_weakness_threshold', -2.0)
    relative_perf = iwm.intraday_change_pct - spy.intraday_change_pct
    triggered = relative_perf <= threshold
    if triggered:
        ctx['value'] = relative_perf
        ctx['extra'] = {'iwm': iwm.intraday_change_pct, 'spy': spy.intraday_change_pct}
    return triggered


def check_defensive_hedge_bid(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for flight to safety (GLD + TLT both up significantly)."""
    gld = snapshot.get('GLD')
    tlt = snapshot.get('TLT')
    if gld is None or tlt is None:
        return False
    threshold = get_threshold('defensive_hedge_bid', 1.5)
    triggered = gld.intraday_change_pct >= threshold and tlt.intraday_change_pct >= threshold
    if triggered:
        ctx['extra'] = {'gld': gld.intraday_change_pct, 'tlt': tlt.intraday_change_pct}
    return triggered


def check_combined_stress(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for combined equity + bond stress (both selling off)."""
    spy = snapshot.get('SPY')
    tlt = snapshot.get('TLT')
    if spy is None or tlt is None:
        return False
    # SPY down -2.5% AND TLT negative same day
    triggered = spy.intraday_change_pct <= -2.5 and tlt.intraday_change_pct < 0
    if triggered:
        ctx['extra'] = {'spy': spy.intraday_change_pct, 'tlt': tlt.intraday_change_pct}
    return triggered


def check_risk_appetite_positive(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for positive risk appetite (broad rally with growth leading)."""
    spy = snapshot.get('SPY')
    qqq = snapshot.get('QQQ')
    if spy is None or qqq is None:
        return False
    triggered = spy.intraday_change_pct >= 1.5 and qqq.intraday_change_pct >= spy.intraday_change_pct
    if triggered:
        ctx['extra'] = {'spy': spy.intraday_change_pct, 'qqq': qqq.intraday_change_pct}
    return triggered


def check_btc_major_move(snapshot: MarketSnapshot, ctx: dict) -> bool:
    """Check for major Bitcoin move (risk sentiment indicator)."""
    btc = snapshot.get('BTC-USD')
    if btc is None:
        return False
    triggered = abs(btc.intraday_change_pct) >= 8.0
    if triggered:
        ctx['value'] = btc.intraday_change_pct
        ctx['symbol'] = 'BTC'
    return triggered


def create_drawdown_checker(level: float):
    """Factory for SPY drawdown rules at specific levels."""
    def check(snapshot: MarketSnapshot, ctx: dict) -> bool:
        spy = snapshot.get('SPY')
        if spy is None:
            return False
        drawdown = get_drawdown_from_high(spy)
        if drawdown is None:
            return False
        # Trigger if drawdown is at or beyond this level but not beyond the next level
        triggered = drawdown <= level
        if triggered:
            ctx['value'] = drawdown
            ctx['symbol'] = 'SPY'
        return triggered
    return check


# Build the rule registry
RULES: list[Rule] = [
    # Critical stress rules
    Rule(
        name="CREDIT_STRESS_INTRADAY",
        severity=Severity.CRITICAL,
        category="Stress",
        description="High yield bonds dropping sharply intraday",
        check=check_credit_stress_intraday,
        message_template="Credit Stress: HYG {value:.1f}% intraday - credit spreads widening",
    ),
    Rule(
        name="COMBINED_STRESS",
        severity=Severity.CRITICAL,
        category="Stress",
        description="Both equities and bonds selling off together",
        check=check_combined_stress,
        message_template="Combined Stress: SPY {spy:.1f}% and TLT {tlt:.1f}% - nowhere to hide",
    ),

    # High severity rules
    Rule(
        name="CREDIT_STRESS_5D",
        severity=Severity.HIGH,
        category="Stress",
        description="Sustained high yield weakness over 5 days",
        check=check_credit_stress_5d,
        message_template="Credit Stress (5D): HYG {value:.1f}% over 5 days - sustained spread widening",
    ),
    Rule(
        name="LIQUIDITY_STRESS_INTRADAY",
        severity=Severity.HIGH,
        category="Stress",
        description="Dollar spiking sharply (liquidity tightening)",
        check=check_liquidity_stress_intraday,
        message_template="Liquidity Stress: DXY +{value:.1f}% intraday - dollar squeeze",
    ),
    Rule(
        name="LIQUIDITY_STRESS_5D",
        severity=Severity.HIGH,
        category="Stress",
        description="Sustained dollar strength over 5 days",
        check=check_liquidity_stress_5d,
        message_template="Liquidity Stress (5D): DXY +{value:.1f}% over 5 days - sustained tightening",
    ),
    Rule(
        name="VOLATILITY_ELEVATED",
        severity=Severity.HIGH,
        category="Stress",
        description="VIX at elevated fear levels",
        check=check_volatility_elevated,
        message_template="Volatility Elevated: VIX at {value:.1f} - fear gauge elevated",
    ),
    Rule(
        name="VOLATILITY_SPIKE",
        severity=Severity.HIGH,
        category="Stress",
        description="VIX spiking sharply intraday",
        check=check_volatility_spike,
        message_template="Volatility Spike: VIX +{value:.1f}% intraday - sudden fear",
    ),

    # Medium severity - Opportunity/Leadership
    Rule(
        name="GROWTH_WEAKNESS",
        severity=Severity.MEDIUM,
        category="Leadership",
        description="Growth/tech underperforming broad market",
        check=check_growth_weakness,
        message_template="Growth Weakness: QQQ underperforming SPY by {value:.1f}%",
    ),
    Rule(
        name="SMALLCAP_WEAKNESS",
        severity=Severity.MEDIUM,
        category="Leadership",
        description="Small caps underperforming (risk-off signal)",
        check=check_smallcap_weakness,
        message_template="Small Cap Weakness: IWM underperforming SPY by {value:.1f}%",
    ),
    Rule(
        name="DEFENSIVE_HEDGE_BID",
        severity=Severity.MEDIUM,
        category="Sentiment",
        description="Flight to safety into gold and treasuries",
        check=check_defensive_hedge_bid,
        message_template="Defensive Bid: GLD +{gld:.1f}% and TLT +{tlt:.1f}% - flight to safety",
    ),

    # Low severity - Informational
    Rule(
        name="RISK_APPETITE_POSITIVE",
        severity=Severity.LOW,
        category="Sentiment",
        description="Positive risk appetite with growth leading",
        check=check_risk_appetite_positive,
        message_template="Risk-On: SPY +{spy:.1f}% with QQQ +{qqq:.1f}% - growth leading",
    ),
    Rule(
        name="BTC_MAJOR_MOVE",
        severity=Severity.LOW,
        category="Sentiment",
        description="Major Bitcoin move (risk sentiment proxy)",
        check=check_btc_major_move,
        message_template="Crypto Signal: BTC {value:+.1f}% - major move in risk sentiment proxy",
    ),
]

# Add SPY drawdown rules at different levels
DRAWDOWN_LEVELS = [-2, -4, -6, -10, -15, -20]
for level in DRAWDOWN_LEVELS:
    abs_level = abs(level)
    severity = Severity.MEDIUM if abs_level <= 6 else Severity.HIGH

    RULES.append(Rule(
        name=f"SPY_DRAWDOWN_{abs_level}PCT",
        severity=severity,
        category="Opportunity",
        description=f"SPY drawdown at {abs_level}% from 52-week high",
        check=create_drawdown_checker(level),
        message_template=f"Drawdown Alert: SPY {{value:.1f}}% from high - {abs_level}% threshold",
    ))


def evaluate_rules(snapshot: MarketSnapshot) -> list[TriggeredRule]:
    """Evaluate all rules against current market snapshot."""
    triggered = []

    for rule in RULES:
        ctx: dict = {}
        try:
            if rule.check(snapshot, ctx):
                triggered.append(TriggeredRule(
                    rule=rule,
                    value=ctx.get('value'),
                    symbol=ctx.get('symbol'),
                    extra_context=ctx.get('extra'),
                ))
        except Exception as e:
            print(f"Error evaluating rule {rule.name}: {e}")

    return triggered


def get_rule_by_name(name: str) -> Optional[Rule]:
    """Get a rule by its name."""
    for rule in RULES:
        if rule.name == name:
            return rule
    return None
