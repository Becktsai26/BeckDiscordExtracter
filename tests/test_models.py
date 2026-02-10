"""Unit tests for core data models (DiscordMessage, TradeSignal, AppConfig).

Tests cover serialization, deserialization, validation, and edge cases.
"""

import json

import pytest

from src.models import (
    AppConfig,
    DiscordMessage,
    ExchangeConfig,
    TradeSignal,
    TradingConfig,
)


# ============================================================
# DiscordMessage Tests
# ============================================================


class TestDiscordMessageToJson:
    """Tests for DiscordMessage.to_json()."""

    def test_to_json_includes_type_field(self):
        """to_json() output must include "type": "DISCORD_MESSAGE"."""
        msg = DiscordMessage(
            author="TraderJoe",
            content="BTC 看多，目標 72000",
            timestamp="2024-01-15T10:30:00.000Z",
            channel="crypto-signals",
        )
        data = json.loads(msg.to_json())
        assert data["type"] == "DISCORD_MESSAGE"

    def test_to_json_contains_all_fields(self):
        """to_json() output must contain author, content, timestamp, channel."""
        msg = DiscordMessage(
            author="Alice",
            content="Hello",
            timestamp="2024-01-01T00:00:00.000Z",
            channel="general",
        )
        data = json.loads(msg.to_json())
        assert data["author"] == "Alice"
        assert data["content"] == "Hello"
        assert data["timestamp"] == "2024-01-01T00:00:00.000Z"
        assert data["channel"] == "general"

    def test_to_json_preserves_unicode(self):
        """to_json() must correctly handle Unicode characters (Chinese, emoji)."""
        msg = DiscordMessage(
            author="交易員",
            content="ETH 做空 🚀",
            timestamp="2024-06-01T12:00:00.000Z",
            channel="幣圈訊號",
        )
        json_str = msg.to_json()
        # Should not escape Unicode
        assert "交易員" in json_str
        assert "🚀" in json_str

    def test_to_json_produces_valid_json(self):
        """to_json() must produce a valid JSON string."""
        msg = DiscordMessage(
            author="Bob",
            content="test message",
            timestamp="2024-01-01T00:00:00.000Z",
            channel="test",
        )
        # Should not raise
        parsed = json.loads(msg.to_json())
        assert isinstance(parsed, dict)


class TestDiscordMessageFromJson:
    """Tests for DiscordMessage.from_json()."""

    def test_from_json_valid_message(self):
        """from_json() should parse a valid JSON string into a DiscordMessage."""
        json_str = json.dumps({
            "type": "DISCORD_MESSAGE",
            "author": "TraderJoe",
            "content": "BTC 看多",
            "timestamp": "2024-01-15T10:30:00.000Z",
            "channel": "crypto-signals",
        })
        msg = DiscordMessage.from_json(json_str)
        assert msg is not None
        assert msg.author == "TraderJoe"
        assert msg.content == "BTC 看多"
        assert msg.timestamp == "2024-01-15T10:30:00.000Z"
        assert msg.channel == "crypto-signals"

    def test_from_json_wrong_type_returns_none(self):
        """from_json() should return None when type is not DISCORD_MESSAGE."""
        json_str = json.dumps({
            "type": "OTHER_TYPE",
            "author": "A",
            "content": "B",
            "timestamp": "C",
            "channel": "D",
        })
        assert DiscordMessage.from_json(json_str) is None

    def test_from_json_missing_type_returns_none(self):
        """from_json() should return None when type field is missing."""
        json_str = json.dumps({
            "author": "A",
            "content": "B",
            "timestamp": "C",
            "channel": "D",
        })
        assert DiscordMessage.from_json(json_str) is None

    def test_from_json_missing_required_field_returns_none(self):
        """from_json() should return None when a required field is missing."""
        # Missing "channel"
        json_str = json.dumps({
            "type": "DISCORD_MESSAGE",
            "author": "A",
            "content": "B",
            "timestamp": "C",
        })
        assert DiscordMessage.from_json(json_str) is None

    def test_from_json_non_string_field_returns_none(self):
        """from_json() should return None when a required field is not a string."""
        json_str = json.dumps({
            "type": "DISCORD_MESSAGE",
            "author": 123,
            "content": "B",
            "timestamp": "C",
            "channel": "D",
        })
        assert DiscordMessage.from_json(json_str) is None

    def test_from_json_invalid_json_returns_none(self):
        """from_json() should return None for malformed JSON."""
        assert DiscordMessage.from_json("not json at all") is None

    def test_from_json_empty_string_returns_none(self):
        """from_json() should return None for an empty string."""
        assert DiscordMessage.from_json("") is None

    def test_from_json_none_input_returns_none(self):
        """from_json() should return None when given None."""
        assert DiscordMessage.from_json(None) is None

    def test_from_json_json_array_returns_none(self):
        """from_json() should return None for a JSON array."""
        assert DiscordMessage.from_json("[1, 2, 3]") is None

    def test_from_json_json_primitive_returns_none(self):
        """from_json() should return None for a JSON primitive."""
        assert DiscordMessage.from_json('"just a string"') is None
        assert DiscordMessage.from_json("42") is None
        assert DiscordMessage.from_json("true") is None
        assert DiscordMessage.from_json("null") is None

    def test_from_json_extra_fields_are_ignored(self):
        """from_json() should succeed even if extra fields are present."""
        json_str = json.dumps({
            "type": "DISCORD_MESSAGE",
            "author": "A",
            "content": "B",
            "timestamp": "C",
            "channel": "D",
            "extra_field": "ignored",
        })
        msg = DiscordMessage.from_json(json_str)
        assert msg is not None
        assert msg.author == "A"


class TestDiscordMessageRoundTrip:
    """Tests for to_json/from_json round-trip consistency."""

    def test_round_trip_basic(self):
        """Serializing then deserializing should produce an equivalent object."""
        original = DiscordMessage(
            author="TraderJoe",
            content="BTC 看多，目標 72000",
            timestamp="2024-01-15T10:30:00.000Z",
            channel="crypto-signals",
        )
        restored = DiscordMessage.from_json(original.to_json())
        assert restored == original

    def test_round_trip_unicode(self):
        """Round-trip should preserve Unicode content."""
        original = DiscordMessage(
            author="交易員",
            content="ETH 做空 🚀 目標 3000",
            timestamp="2024-06-01T12:00:00.000Z",
            channel="幣圈訊號",
        )
        restored = DiscordMessage.from_json(original.to_json())
        assert restored == original


# ============================================================
# TradeSignal Tests
# ============================================================


class TestTradeSignalValidate:
    """Tests for TradeSignal.validate()."""

    def test_valid_buy_signal(self):
        """A valid BUY signal should pass validation."""
        signal = TradeSignal(
            symbol="BTC/USDT",
            side="BUY",
            confidence=85,
            summary="BTC 看多，目標 72000",
        )
        assert signal.validate() == []

    def test_valid_sell_signal(self):
        """A valid SELL signal should pass validation."""
        signal = TradeSignal(
            symbol="ETH/USDT",
            side="SELL",
            confidence=60,
            summary="ETH bearish signal",
        )
        assert signal.validate() == []

    def test_valid_boundary_confidence_zero(self):
        """Confidence of 0 should be valid."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=0, summary="Low confidence")
        assert signal.validate() == []

    def test_valid_boundary_confidence_hundred(self):
        """Confidence of 100 should be valid."""
        signal = TradeSignal(symbol="BTC/USDT", side="SELL", confidence=100, summary="High confidence")
        assert signal.validate() == []

    def test_invalid_side(self):
        """Side other than BUY/SELL should fail validation."""
        signal = TradeSignal(symbol="BTC/USDT", side="HOLD", confidence=50, summary="test")
        errors = signal.validate()
        assert len(errors) > 0
        assert any("side" in e for e in errors)

    def test_invalid_side_lowercase(self):
        """Lowercase 'buy' should fail validation (must be uppercase)."""
        signal = TradeSignal(symbol="BTC/USDT", side="buy", confidence=50, summary="test")
        errors = signal.validate()
        assert any("side" in e for e in errors)

    def test_confidence_below_zero(self):
        """Confidence below 0 should fail validation."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=-1, summary="test")
        errors = signal.validate()
        assert any("confidence" in e for e in errors)

    def test_confidence_above_hundred(self):
        """Confidence above 100 should fail validation."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=101, summary="test")
        errors = signal.validate()
        assert any("confidence" in e for e in errors)

    def test_empty_symbol(self):
        """Empty symbol should fail validation."""
        signal = TradeSignal(symbol="", side="BUY", confidence=50, summary="test")
        errors = signal.validate()
        assert any("symbol" in e for e in errors)

    def test_whitespace_only_symbol(self):
        """Whitespace-only symbol should fail validation."""
        signal = TradeSignal(symbol="   ", side="BUY", confidence=50, summary="test")
        errors = signal.validate()
        assert any("symbol" in e for e in errors)

    def test_empty_summary(self):
        """Empty summary should fail validation."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=50, summary="")
        errors = signal.validate()
        assert any("summary" in e for e in errors)

    def test_whitespace_only_summary(self):
        """Whitespace-only summary should fail validation."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=50, summary="   ")
        errors = signal.validate()
        assert any("summary" in e for e in errors)

    def test_multiple_errors(self):
        """Multiple invalid fields should produce multiple errors."""
        signal = TradeSignal(symbol="", side="HOLD", confidence=200, summary="")
        errors = signal.validate()
        assert len(errors) == 4

    def test_confidence_boolean_rejected(self):
        """Boolean values for confidence should be rejected (bool is subclass of int)."""
        signal = TradeSignal(symbol="BTC/USDT", side="BUY", confidence=True, summary="test")
        errors = signal.validate()
        assert any("confidence" in e for e in errors)


# ============================================================
# Config Dataclass Tests
# ============================================================


class TestExchangeConfig:
    """Tests for ExchangeConfig dataclass."""

    def test_default_values(self):
        """ExchangeConfig should have correct defaults."""
        config = ExchangeConfig(name="binance")
        assert config.name == "binance"
        assert config.api_key == ""
        assert config.api_secret == ""
        assert config.enabled is False

    def test_custom_values(self):
        """ExchangeConfig should accept custom values."""
        config = ExchangeConfig(
            name="bybit",
            api_key="key123",
            api_secret="secret456",
            enabled=True,
        )
        assert config.name == "bybit"
        assert config.api_key == "key123"
        assert config.api_secret == "secret456"
        assert config.enabled is True


class TestTradingConfig:
    """Tests for TradingConfig dataclass."""

    def test_default_values(self):
        """TradingConfig should have correct defaults."""
        config = TradingConfig()
        assert config.confidence_threshold == 70
        assert config.max_trade_amount_usdt == 100.0
        assert config.enabled_exchanges == []

    def test_custom_values(self):
        """TradingConfig should accept custom values."""
        config = TradingConfig(
            confidence_threshold=80,
            max_trade_amount_usdt=500.0,
            enabled_exchanges=["binance", "bybit"],
        )
        assert config.confidence_threshold == 80
        assert config.max_trade_amount_usdt == 500.0
        assert config.enabled_exchanges == ["binance", "bybit"]


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self):
        """AppConfig should have correct defaults."""
        config = AppConfig()
        assert config.cdp_url == "http://localhost:9222"
        assert config.target_channels == []
        assert config.exchanges == []
        assert isinstance(config.trading, TradingConfig)
        assert config.read_only_mode is True
        assert config.llm_model == "gpt-4o-mini"
        assert config.llm_api_key == ""

    def test_read_only_mode_default_true(self):
        """AppConfig.read_only_mode must default to True (Requirement 11.5)."""
        config = AppConfig()
        assert config.read_only_mode is True

    def test_custom_values(self):
        """AppConfig should accept custom values."""
        exchanges = [ExchangeConfig(name="binance", enabled=True)]
        trading = TradingConfig(confidence_threshold=80)
        config = AppConfig(
            cdp_url="http://localhost:9333",
            target_channels=["crypto-signals"],
            exchanges=exchanges,
            trading=trading,
            read_only_mode=False,
            llm_model="gpt-4",
            llm_api_key="sk-test",
        )
        assert config.cdp_url == "http://localhost:9333"
        assert config.target_channels == ["crypto-signals"]
        assert len(config.exchanges) == 1
        assert config.exchanges[0].name == "binance"
        assert config.trading.confidence_threshold == 80
        assert config.read_only_mode is False
        assert config.llm_model == "gpt-4"
        assert config.llm_api_key == "sk-test"
