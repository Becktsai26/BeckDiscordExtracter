"""Config Manager module.

Responsible for loading, validating, and managing YAML configuration files.
"""

import os
from typing import Optional

import yaml

from src.models import AppConfig, ExchangeConfig, TradingConfig

# Valid exchange names
VALID_EXCHANGE_NAMES = {"binance", "bybit", "mexc"}


class ConfigManager:
    """Manages loading, validating, saving, and generating YAML configuration files.

    The load() method returns a tuple of (AppConfig or None, list[str] errors).
    When the file doesn't exist, generate_default() is called first, then the
    generated file is loaded. When the YAML is malformed or fields are invalid,
    errors are returned.
    """

    def load(self, path: str) -> tuple[Optional[AppConfig], list[str]]:
        """Load configuration from a YAML file and convert to AppConfig.

        If the file does not exist, generate_default() is called to create a
        default config file, then the generated file is loaded.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            A tuple of (AppConfig or None, list of error messages).
            If loading and validation succeed, returns (AppConfig, []).
            If there are errors, returns (None, [error messages]).
        """
        if not os.path.exists(path):
            self.generate_default(path)

        # Read and parse YAML
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return None, [f"YAML 語法錯誤: {e}"]
        except OSError as e:
            return None, [f"無法讀取設定檔: {e}"]

        if raw is None:
            return None, ["設定檔為空"]

        if not isinstance(raw, dict):
            return None, ["設定檔格式錯誤: 最上層必須為字典"]

        # Convert raw dict to AppConfig
        config, parse_errors = self._parse_config(raw)
        if parse_errors:
            return None, parse_errors

        # Validate the parsed config
        validation_errors = self.validate(config)
        if validation_errors:
            return None, validation_errors

        return config, []

    def validate(self, config: AppConfig) -> list[str]:
        """Validate an AppConfig instance.

        Checks all fields according to the design spec validation rules:
        - target_channels: must not be None (can be empty list, triggers warning)
        - exchanges[].name: must be one of "binance", "bybit", "mexc"
        - exchanges[].api_key: if enabled=true, must not be empty
        - trading.confidence_threshold: integer 0-100
        - trading.max_trade_amount_usdt: positive number
        - read_only_mode: must be boolean, defaults to true
        - llm_api_key: must not be empty

        Args:
            config: The AppConfig to validate.

        Returns:
            A list of error messages. An empty list means validation passed.
        """
        errors: list[str] = []

        # Validate target_channels
        if config.target_channels is None:
            errors.append("target_channels 不可為 null")

        # Validate exchanges
        if config.exchanges is not None:
            for i, exchange in enumerate(config.exchanges):
                if exchange.name not in VALID_EXCHANGE_NAMES:
                    errors.append(
                        f"exchanges[{i}].name 必須為 'binance'、'bybit'、'mexc' 之一，"
                        f"目前為 '{exchange.name}'"
                    )
                if exchange.enabled and not exchange.api_key:
                    errors.append(
                        f"exchanges[{i}].api_key 不可為空（當 enabled=true 時），"
                        f"交易所: {exchange.name}"
                    )

        # Validate trading config
        if not isinstance(config.trading.confidence_threshold, int) or isinstance(
            config.trading.confidence_threshold, bool
        ):
            errors.append("trading.confidence_threshold 必須為整數")
        elif config.trading.confidence_threshold < 0 or config.trading.confidence_threshold > 100:
            errors.append("trading.confidence_threshold 必須在 0-100 之間")

        if not isinstance(config.trading.max_trade_amount_usdt, (int, float)) or isinstance(
            config.trading.max_trade_amount_usdt, bool
        ):
            errors.append("trading.max_trade_amount_usdt 必須為數字")
        elif config.trading.max_trade_amount_usdt <= 0:
            errors.append("trading.max_trade_amount_usdt 必須為正數")

        # Validate read_only_mode
        if not isinstance(config.read_only_mode, bool):
            errors.append("read_only_mode 必須為布林值")

        # Validate llm_api_key
        if not config.llm_api_key:
            errors.append("llm.api_key 不可為空")

        return errors

    def generate_default(self, path: str) -> None:
        """Generate a default configuration file with comments.

        Creates a YAML file with sensible defaults and explanatory comments
        to guide the user in configuring the application.

        Args:
            path: Path where the default config file will be written.
        """
        default_content = """\
# Discord 訊息監聽與自動交易工具 - 設定檔
# 請根據您的需求修改以下設定

# Chrome DevTools Protocol 連線 URL
cdp_url: "http://localhost:9222"

# 只讀模式（預設為 true，僅監聽訊息不執行交易）
read_only_mode: true

# 目標 Discord 頻道清單（僅監聽這些頻道的訊息）
target_channels:
  - "crypto-signals"
  - "trading-alerts"

# 交易所設定
exchanges:
  - name: "binance"
    api_key: ""
    api_secret: ""
    enabled: false
  - name: "bybit"
    api_key: ""
    api_secret: ""
    enabled: false
  - name: "mexc"
    api_key: ""
    api_secret: ""
    enabled: false

# 交易參數設定
trading:
  # 信心度閾值（0-100），低於此值的交易信號將被忽略
  confidence_threshold: 70
  # 每筆交易最大金額（USDT）
  max_trade_amount_usdt: 100.0
  # 啟用的交易所清單
  enabled_exchanges:
    - "binance"

# LLM 設定
llm:
  model: "gpt-4o-mini"
  api_key: ""
"""
        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(default_content)

    def save(self, config: AppConfig, path: str) -> None:
        """Save an AppConfig to a YAML file.

        Converts the AppConfig dataclass to a dictionary and writes it as YAML.
        This method is primarily used for property-based testing (round-trip tests).

        Args:
            config: The AppConfig to save.
            path: Path where the config file will be written.
        """
        data = self._config_to_dict(config)

        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def _parse_config(self, raw: dict) -> tuple[Optional[AppConfig], list[str]]:
        """Parse a raw dictionary into an AppConfig.

        Args:
            raw: Dictionary loaded from YAML.

        Returns:
            A tuple of (AppConfig or None, list of parse error messages).
        """
        errors: list[str] = []

        try:
            # Parse cdp_url
            cdp_url = raw.get("cdp_url", "http://localhost:9222")
            if not isinstance(cdp_url, str):
                errors.append("cdp_url 必須為字串")
                cdp_url = "http://localhost:9222"

            # Parse read_only_mode
            read_only_mode = raw.get("read_only_mode", True)

            # Parse target_channels
            target_channels = raw.get("target_channels")
            if target_channels is None:
                target_channels = []
            elif not isinstance(target_channels, list):
                errors.append("target_channels 必須為清單")
                return None, errors

            # Parse exchanges
            exchanges_raw = raw.get("exchanges", [])
            exchanges: list[ExchangeConfig] = []
            if exchanges_raw is None:
                exchanges_raw = []
            elif not isinstance(exchanges_raw, list):
                errors.append("exchanges 必須為清單")
                return None, errors

            for i, ex_raw in enumerate(exchanges_raw):
                if not isinstance(ex_raw, dict):
                    errors.append(f"exchanges[{i}] 必須為字典")
                    continue
                exchanges.append(
                    ExchangeConfig(
                        name=str(ex_raw.get("name", "")),
                        api_key=str(ex_raw.get("api_key", "")),
                        api_secret=str(ex_raw.get("api_secret", "")),
                        enabled=bool(ex_raw.get("enabled", False)),
                    )
                )

            # Parse trading config
            trading_raw = raw.get("trading", {})
            if trading_raw is None:
                trading_raw = {}
            elif not isinstance(trading_raw, dict):
                errors.append("trading 必須為字典")
                return None, errors

            trading = TradingConfig(
                confidence_threshold=trading_raw.get("confidence_threshold", 70),
                max_trade_amount_usdt=trading_raw.get("max_trade_amount_usdt", 100.0),
                enabled_exchanges=trading_raw.get("enabled_exchanges", []) or [],
            )

            # Parse LLM settings
            llm_raw = raw.get("llm", {})
            if llm_raw is None:
                llm_raw = {}
            elif not isinstance(llm_raw, dict):
                errors.append("llm 必須為字典")
                return None, errors

            llm_model = llm_raw.get("model", "gpt-4o-mini")
            if not isinstance(llm_model, str):
                llm_model = "gpt-4o-mini"

            llm_api_key = str(llm_raw.get("api_key", ""))

            if errors:
                return None, errors

            config = AppConfig(
                cdp_url=cdp_url,
                target_channels=target_channels,
                exchanges=exchanges,
                trading=trading,
                read_only_mode=read_only_mode,
                llm_model=llm_model,
                llm_api_key=llm_api_key,
            )

            return config, []

        except Exception as e:
            return None, [f"設定檔解析錯誤: {e}"]

    @staticmethod
    def _config_to_dict(config: AppConfig) -> dict:
        """Convert an AppConfig to a plain dictionary suitable for YAML serialization.

        Args:
            config: The AppConfig to convert.

        Returns:
            A dictionary representation of the config.
        """
        return {
            "cdp_url": config.cdp_url,
            "read_only_mode": config.read_only_mode,
            "target_channels": config.target_channels,
            "exchanges": [
                {
                    "name": ex.name,
                    "api_key": ex.api_key,
                    "api_secret": ex.api_secret,
                    "enabled": ex.enabled,
                }
                for ex in config.exchanges
            ],
            "trading": {
                "confidence_threshold": config.trading.confidence_threshold,
                "max_trade_amount_usdt": config.trading.max_trade_amount_usdt,
                "enabled_exchanges": config.trading.enabled_exchanges,
            },
            "llm": {
                "model": config.llm_model,
                "api_key": config.llm_api_key,
            },
        }
