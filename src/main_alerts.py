"""Intraday alerts entry point."""

import sys
from src.data import fetch_market_snapshot
from src.rules import evaluate_rules
from src.storage import should_fire, record_fire
from src.render import render_alert, render_multiple_alerts
from src.telegram import send_message_safe


def main():
    """Main entry point for intraday alert checks."""
    print("Fetching market data...")
    snapshot = fetch_market_snapshot()

    if not snapshot.data:
        print("Error: No market data fetched")
        sys.exit(1)

    print(f"Data fetched for {len(snapshot.data)} symbols")

    # Evaluate all rules
    print("Evaluating rules...")
    triggered = evaluate_rules(snapshot)

    if not triggered:
        print("No rules triggered")
        return

    print(f"{len(triggered)} rule(s) triggered before cooldown check")

    # Filter by cooldowns
    alerts_to_send = []
    for tr in triggered:
        if should_fire(tr.rule.name, tr.rule.severity):
            alerts_to_send.append(tr)
            print(f"  FIRE: {tr.rule.name} ({tr.rule.severity.value})")
        else:
            print(f"  SKIP (cooldown): {tr.rule.name}")

    if not alerts_to_send:
        print("All triggered rules are in cooldown")
        return

    # Sort by severity (critical first)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    alerts_to_send.sort(key=lambda tr: severity_order.get(tr.rule.severity.value, 99))

    # Send alerts
    print(f"Sending {len(alerts_to_send)} alert(s)...")

    if len(alerts_to_send) <= 3:
        # Send individual alerts
        for tr in alerts_to_send:
            message = render_alert(tr, snapshot)
            success = send_message_safe(message)
            if success:
                record_fire(tr.rule.name)
                print(f"  Sent: {tr.rule.name}")
            else:
                print(f"  FAILED: {tr.rule.name}")
    else:
        # Combine into single message to avoid spam
        message = render_multiple_alerts(alerts_to_send, snapshot)
        success = send_message_safe(message)
        if success:
            for tr in alerts_to_send:
                record_fire(tr.rule.name)
            print(f"  Sent combined alert with {len(alerts_to_send)} signals")
        else:
            print("  FAILED to send combined alert")

    print("Done")


if __name__ == "__main__":
    main()
