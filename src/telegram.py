"""Telegram API wrapper for sending messages."""

import os
import requests
from typing import Optional


def get_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get Telegram credentials from environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    return bot_token, chat_id


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message via Telegram bot.

    Args:
        text: Message text (supports Markdown formatting)
        parse_mode: Telegram parse mode ("Markdown" or "HTML")

    Returns:
        True if message was sent successfully, False otherwise
    """
    bot_token, chat_id = get_credentials()

    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            return True
        else:
            print(f"Telegram API error: {result.get('description', 'Unknown error')}")
            return False

    except requests.exceptions.Timeout:
        print("Error: Telegram API request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        return False


def send_message_safe(text: str) -> bool:
    """
    Send message with fallback to plain text if Markdown fails.

    Some special characters can break Markdown parsing.
    This function tries Markdown first, then falls back to plain text.
    """
    # First try with Markdown
    if send_message(text, parse_mode="Markdown"):
        return True

    # Fallback: strip Markdown formatting and send as plain text
    plain_text = text.replace("*", "").replace("_", "").replace("`", "")
    return send_message(plain_text, parse_mode="")


def test_connection() -> bool:
    """Test Telegram bot connection."""
    bot_token, chat_id = get_credentials()

    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/getMe"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            bot_info = result.get("result", {})
            print(f"Connected to bot: @{bot_info.get('username', 'unknown')}")
            return True
        else:
            print(f"Telegram API error: {result.get('description', 'Unknown error')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Telegram: {e}")
        return False
