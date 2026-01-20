"""Daily report entry point."""

import sys
from src.data import fetch_market_snapshot
from src.rules import evaluate_rules
from src.regime import assess_regime
from src.render import render_daily_report
from src.telegram import send_message_safe


def main():
    """Main entry point for daily market report."""
    print("Fetching market data...")
    snapshot = fetch_market_snapshot()

    if not snapshot.data:
        print("Error: No market data fetched")
        sys.exit(1)

    print(f"Data fetched for {len(snapshot.data)} symbols")

    # Assess regime
    print("Assessing market regime...")
    regime = assess_regime(snapshot)
    print(f"Regime: {regime.regime.value}")
    if regime.triggers:
        for trigger in regime.triggers:
            print(f"  - {trigger}")

    # Evaluate all rules (ignore cooldowns for daily summary)
    print("Evaluating rules...")
    triggered = evaluate_rules(snapshot)
    print(f"{len(triggered)} rule(s) triggered")

    # Render daily report
    print("Rendering daily report...")
    report = render_daily_report(snapshot, regime, triggered)

    # Send to Telegram
    print("Sending daily report...")
    success = send_message_safe(report)

    if success:
        print("Daily report sent successfully")
    else:
        print("Failed to send daily report")
        sys.exit(1)

    print("Done")


if __name__ == "__main__":
    main()
