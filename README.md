**!!! Work in Progress; Don't attempt to use or fork !!!**

# Market Policy Bot

A modular market monitoring system that delivers regime-aware alerts and daily reports via Telegram. Designed as a forkable template for systematic traders.

## Features

- **Regime Assessment**: Automatically classifies market conditions as NORMAL or DEFENSIVE based on credit, volatility, and liquidity signals
- **Multi-Tier Alerts**: Critical, High, Medium, and Low severity alerts with configurable cooldowns
- **Daily Reports**: End-of-day summary with market snapshot, regime status, and triggered signals
- **Privacy-First Design**: All thresholds in gitignored config file; credentials in GitHub Secrets

## Architecture

```
src/
├── data.py          # Market data fetching (yfinance)
├── indicators.py    # Calculated metrics (returns, drawdowns, etc.)
├── rules.py         # Rule registry with severity levels
├── regime.py        # NORMAL vs DEFENSIVE assessment
├── render.py        # Telegram message formatting
├── storage.py       # JSON state persistence for cooldowns
├── telegram.py      # Telegram API wrapper
├── main_alerts.py   # Intraday alerts entry point
└── main_daily.py    # Daily report entry point
```

## Quick Start

### 1. Fork This Repository

Click the **Fork** button to create your own copy.

### 2. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save your bot token (looks like `123456789:ABCdefGHI...`)
4. Start a chat with your new bot
5. Get your Chat ID:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":123456789}` and save that number

### 3. Configure GitHub Secrets

Go to your repo's **Settings** → **Secrets and variables** → **Actions** and add:

| Secret Name | Value |
|-------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from step 2 |
| `TELEGRAM_CHAT_ID` | Your chat ID from step 2 |

### 4. Customize Thresholds (Optional)

Copy `config.example.yml` to `config.yml` and adjust the thresholds to match your risk preferences. The config file is gitignored, so your settings stay private.

### 5. Enable GitHub Actions

1. Go to the **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**

That's it! The bot will now:
- Check for alerts every 15 minutes during market hours
- Send a daily report at market close

### 6. Test Manually

Go to **Actions** → select a workflow → **Run workflow** to test immediately.

## Configuration

### Regime Thresholds

The market shifts to DEFENSIVE if any of these conditions are met:

| Condition | Default | Description |
|-----------|---------|-------------|
| HYG 5D return | ≤ -3.0% | Credit stress / spread widening |
| DXY 5D return | ≥ +2.0% | Dollar strength / liquidity tightening |
| VIX level | ≥ 30 | Elevated volatility (AND rising) |
| SPY + TLT | Both negative | Combined equity/bond stress |

### Alert Categories

| Category | Severity | Examples |
|----------|----------|----------|
| Stress | Critical/High | Credit stress, liquidity stress, volatility spike |
| Opportunity | Medium/High | SPY drawdown alerts at -2%, -4%, -6%, -10%, -15%, -20% |
| Leadership | Medium | Growth weakness, small cap weakness |
| Sentiment | Low/Medium | Flight to safety, risk appetite signals |

### Cooldowns

Alerts won't re-fire until the cooldown expires:

| Severity | Default Cooldown |
|----------|-----------------|
| Critical | 45 minutes |
| High | 90 minutes |
| Medium | 4 hours |
| Low | 24 hours |

## Tracked Instruments

| Symbol | Description |
|--------|-------------|
| SPY | S&P 500 ETF |
| QQQ | Nasdaq-100 ETF |
| IWM | Russell 2000 ETF |
| ^TNX | 10-Year Treasury Yield |
| TLT | 20+ Year Treasury ETF |
| HYG | High Yield Corporate Bond ETF |
| ^VIX | Volatility Index |
| DX-Y.NYB | US Dollar Index |
| GLD | Gold ETF |
| BTC-USD | Bitcoin |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy config template
cp config.example.yml config.yml

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Run daily report
python -m src.main_daily

# Run intraday alerts
python -m src.main_alerts
```

## Schedule

| Workflow | Schedule | Description |
|----------|----------|-------------|
| Intraday Alerts | Every 15 min, 9 AM - 4 PM ET | Check rules and send alerts |
| Daily Close Report | 4:20 PM ET | Full market summary |

## Privacy Design

This is a **forkable template** - all sensitive data stays private:

- **config.yml** - Your thresholds (gitignored)
- **GitHub Secrets** - Telegram credentials (encrypted)
- **GitHub Actions cache** - Alert cooldown state (private)
- **No hardcoded values** - Everything loaded from config

## License

MIT License - feel free to use and modify.

---

**Built with:** Python, GitHub Actions, Telegram Bot API, Yahoo Finance API
