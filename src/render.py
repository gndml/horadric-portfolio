"""Telegram message rendering and formatting."""

from datetime import datetime
from typing import Optional
from src.data import MarketSnapshot
from src.rules import TriggeredRule, Severity
from src.regime import RegimeAssessment, Regime, get_regime_emoji, get_regime_action_guidance
from src.indicators import format_pct, format_price, get_drawdown_from_high


def get_severity_emoji(severity: Severity) -> str:
    """Get emoji for severity level."""
    return {
        Severity.CRITICAL: "🚨",
        Severity.HIGH: "⚠️",
        Severity.MEDIUM: "📊",
        Severity.LOW: "ℹ️",
    }.get(severity, "📌")


def get_change_emoji(change: float) -> str:
    """Get emoji based on price change direction."""
    if change >= 1.5:
        return "🟢"
    elif change >= 0:
        return "🔹"
    elif change >= -1.5:
        return "🔸"
    else:
        return "🔴"


def render_alert(triggered: TriggeredRule, snapshot: MarketSnapshot) -> str:
    """Render a single alert message."""
    rule = triggered.rule
    emoji = get_severity_emoji(rule.severity)

    # Build message from template
    format_args = {}
    if triggered.value is not None:
        format_args['value'] = triggered.value
    if triggered.extra_context:
        format_args.update(triggered.extra_context)

    try:
        message_body = rule.message_template.format(**format_args)
    except KeyError:
        message_body = rule.message_template

    lines = [
        f"{emoji} *{rule.severity.value.upper()}* - {rule.category}",
        "",
        message_body,
        "",
        f"_{datetime.now().strftime('%H:%M:%S ET')}_",
    ]

    return "\n".join(lines)


def render_daily_report(
    snapshot: MarketSnapshot,
    regime: RegimeAssessment,
    triggered_rules: list[TriggeredRule],
) -> str:
    """Render the full daily market report."""
    lines = []

    # Header
    lines.append("*📊 Daily Market Report*")
    lines.append(f"_{snapshot.timestamp.strftime('%Y-%m-%d %H:%M ET')}_")
    lines.append("")

    # TL;DR Summary
    lines.append("*TL;DR*")
    lines.append(_generate_tldr(snapshot, regime, triggered_rules))
    lines.append("")

    # Regime Assessment
    regime_emoji = get_regime_emoji(regime.regime)
    lines.append(f"*Regime: {regime_emoji} {regime.regime.value}*")
    if regime.triggers:
        for trigger in regime.triggers[:3]:  # Limit to top 3
            lines.append(f"  • {trigger}")
    lines.append(f"_{get_regime_action_guidance(regime.regime)}_")
    lines.append("")

    # Daily Metrics Snapshot
    lines.append("*Market Snapshot*")
    lines.append("```")

    # Equities section
    lines.append("Equities:")
    for sym in ['SPY', 'QQQ', 'IWM']:
        data = snapshot.get(sym)
        if data:
            change_1d = format_pct(data.intraday_change_pct)
            change_5d = format_pct(data.change_5d_pct) if data.change_5d_pct else "N/A"
            lines.append(f"  {sym:6} {format_price(data.current_price):>10}  1D:{change_1d:>7}  5D:{change_5d:>7}")

    # Rates & Bonds
    lines.append("Rates & Bonds:")
    for sym, label in [('^TNX', '10Y'), ('TLT', 'TLT'), ('HYG', 'HYG')]:
        data = snapshot.get(sym)
        if data:
            change_1d = format_pct(data.intraday_change_pct)
            change_5d = format_pct(data.change_5d_pct) if data.change_5d_pct else "N/A"
            lines.append(f"  {label:6} {format_price(data.current_price, sym):>10}  1D:{change_1d:>7}  5D:{change_5d:>7}")

    # Risk Indicators
    lines.append("Risk Indicators:")
    for sym, label in [('^VIX', 'VIX'), ('DX-Y.NYB', 'DXY')]:
        data = snapshot.get(sym)
        if data:
            change_1d = format_pct(data.intraday_change_pct)
            lines.append(f"  {label:6} {format_price(data.current_price, sym):>10}  1D:{change_1d:>7}")

    # Alternatives
    lines.append("Alternatives:")
    for sym in ['GLD', 'BTC-USD']:
        data = snapshot.get(sym)
        if data:
            change_1d = format_pct(data.intraday_change_pct)
            change_5d = format_pct(data.change_5d_pct) if data.change_5d_pct else "N/A"
            label = 'GLD' if sym == 'GLD' else 'BTC'
            lines.append(f"  {label:6} {format_price(data.current_price, sym):>10}  1D:{change_1d:>7}  5D:{change_5d:>7}")

    lines.append("```")
    lines.append("")

    # SPY Drawdown Status
    spy = snapshot.get('SPY')
    if spy:
        drawdown = get_drawdown_from_high(spy)
        if drawdown is not None:
            lines.append(f"*SPY Drawdown:* {drawdown:.1f}% from 52w high")
            lines.append("")

    # Rules Triggered Summary
    if triggered_rules:
        lines.append("*Signals Triggered*")
        # Group by severity
        by_severity = {}
        for tr in triggered_rules:
            sev = tr.rule.severity
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(tr)

        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            if severity in by_severity:
                emoji = get_severity_emoji(severity)
                for tr in by_severity[severity]:
                    lines.append(f"  {emoji} {tr.rule.name}")
    else:
        lines.append("_No alert signals triggered_")

    return "\n".join(lines)


def _generate_tldr(
    snapshot: MarketSnapshot,
    regime: RegimeAssessment,
    triggered_rules: list[TriggeredRule],
) -> str:
    """Generate 1-2 sentence summary of market conditions."""
    spy = snapshot.get('SPY')
    vix = snapshot.get('^VIX')

    parts = []

    # Market direction
    if spy:
        if spy.intraday_change_pct >= 1.0:
            parts.append("Strong risk-on day")
        elif spy.intraday_change_pct >= 0.3:
            parts.append("Modest gains")
        elif spy.intraday_change_pct >= -0.3:
            parts.append("Flat session")
        elif spy.intraday_change_pct >= -1.0:
            parts.append("Modest weakness")
        else:
            parts.append("Significant selling")

    # Volatility context
    if vix:
        if vix.current_price >= 30:
            parts.append("elevated fear")
        elif vix.current_price <= 15:
            parts.append("low volatility")

    # Regime note
    if regime.regime == Regime.DEFENSIVE:
        critical_count = sum(1 for tr in triggered_rules if tr.rule.severity == Severity.CRITICAL)
        if critical_count > 0:
            parts.append(f"{critical_count} critical signal(s)")
        else:
            parts.append("defensive posture warranted")

    # Combine
    if len(parts) >= 2:
        return f"{parts[0]} with {', '.join(parts[1:])}."
    elif parts:
        return f"{parts[0]}."
    else:
        return "Market conditions normal."


def render_multiple_alerts(triggered_rules: list[TriggeredRule], snapshot: MarketSnapshot) -> str:
    """Render multiple alerts in a single message."""
    if len(triggered_rules) == 1:
        return render_alert(triggered_rules[0], snapshot)

    lines = [
        f"*🔔 {len(triggered_rules)} Alerts Triggered*",
        f"_{datetime.now().strftime('%H:%M:%S ET')}_",
        "",
    ]

    for tr in triggered_rules:
        emoji = get_severity_emoji(tr.rule.severity)
        format_args = {}
        if tr.value is not None:
            format_args['value'] = tr.value
        if tr.extra_context:
            format_args.update(tr.extra_context)

        try:
            message_body = tr.rule.message_template.format(**format_args)
        except KeyError:
            message_body = tr.rule.description

        lines.append(f"{emoji} *{tr.rule.severity.value.upper()}*: {message_body}")

    return "\n".join(lines)
