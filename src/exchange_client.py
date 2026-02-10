"""Exchange Client module.

Interfaces with cryptocurrency exchanges (Binance, Bybit, MEXC) via CCXT.
"""

import logging
from typing import Optional

import ccxt

from src.models import ExchangeConfig, TradingConfig, TradeSignal


logger = logging.getLogger(__name__)


class ExchangeClient:
    """Client for interacting with cryptocurrency exchanges via CCXT.
    
    Supports Binance, Bybit, and MEXC exchanges. Handles order placement
    with confidence threshold and amount limit checks.
    """

    # Supported exchange names mapped to CCXT exchange classes
    SUPPORTED_EXCHANGES = {
        "binance": ccxt.binance,
        "bybit": ccxt.bybit,
        "mexc": ccxt.mexc,
    }

    def __init__(
        self,
        exchanges_config: list[ExchangeConfig],
        trading_config: TradingConfig,
    ):
        """Initialize the ExchangeClient.
        
        Args:
            exchanges_config: List of exchange configurations.
            trading_config: Trading parameters including thresholds and limits.
        """
        self.exchanges: dict[str, ccxt.Exchange] = {}
        self.trading_config = trading_config
        self._init_exchanges(exchanges_config)

    def _init_exchanges(self, configs: list[ExchangeConfig]) -> None:
        """Initialize enabled exchange connections using CCXT.
        
        Only initializes exchanges that are:
        1. Enabled in the configuration
        2. Supported by this client (Binance, Bybit, MEXC)
        
        Args:
            configs: List of exchange configurations.
        """
        for config in configs:
            if not config.enabled:
                logger.debug(f"Exchange '{config.name}' is disabled, skipping.")
                continue

            exchange_name = config.name.lower()
            
            if exchange_name not in self.SUPPORTED_EXCHANGES:
                logger.warning(
                    f"Exchange '{config.name}' is not supported. "
                    f"Supported exchanges: {list(self.SUPPORTED_EXCHANGES.keys())}"
                )
                continue

            try:
                exchange_class = self.SUPPORTED_EXCHANGES[exchange_name]
                exchange_instance = exchange_class({
                    "apiKey": config.api_key,
                    "secret": config.api_secret,
                    "enableRateLimit": True,
                })
                self.exchanges[exchange_name] = exchange_instance
                logger.info(f"Successfully initialized exchange: {exchange_name}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize exchange '{exchange_name}': {e}"
                )

    def _check_confidence(self, signal: TradeSignal) -> bool:
        """Check if the signal confidence meets the threshold.
        
        Args:
            signal: The trade signal to check.
            
        Returns:
            True if confidence >= threshold, False otherwise.
        """
        return signal.confidence >= self.trading_config.confidence_threshold

    def _check_amount_limit(self, amount_usdt: float) -> bool:
        """Check if the trade amount is within the limit.
        
        Args:
            amount_usdt: The trade amount in USDT.
            
        Returns:
            True if amount <= max_trade_amount_usdt, False otherwise.
        """
        return amount_usdt <= self.trading_config.max_trade_amount_usdt

    async def place_order(
        self,
        signal: TradeSignal,
        exchange_name: str,
        amount_usdt: float = 0.0,
    ) -> Optional[dict]:
        """Place an order on the specified exchange based on the trade signal.
        
        Performs the following checks before placing an order:
        1. Confidence threshold check - skips if confidence is too low
        2. Amount limit check - skips if amount exceeds the maximum
        
        On success, logs order details (order ID, symbol, side, amount, price).
        On failure, catches the exception and logs the error without crashing.
        
        Args:
            signal: The trade signal containing symbol, side, confidence, etc.
            exchange_name: The name of the exchange to place the order on.
            amount_usdt: The trade amount in USDT (default: max_trade_amount_usdt).
            
        Returns:
            Order details dict on success, None if order was skipped or failed.
        """
        exchange_name = exchange_name.lower()
        
        # Use default amount if not specified
        if amount_usdt <= 0:
            amount_usdt = self.trading_config.max_trade_amount_usdt

        # Check if exchange is initialized
        if exchange_name not in self.exchanges:
            logger.warning(
                f"Exchange '{exchange_name}' is not initialized. "
                f"Available exchanges: {list(self.exchanges.keys())}"
            )
            return None

        # Check confidence threshold
        if not self._check_confidence(signal):
            logger.info(
                f"Skipping order: confidence {signal.confidence} is below "
                f"threshold {self.trading_config.confidence_threshold} "
                f"(symbol: {signal.symbol}, side: {signal.side})"
            )
            return None

        # Check amount limit
        if not self._check_amount_limit(amount_usdt):
            logger.info(
                f"Skipping order: amount {amount_usdt} USDT exceeds "
                f"maximum {self.trading_config.max_trade_amount_usdt} USDT "
                f"(symbol: {signal.symbol}, side: {signal.side})"
            )
            return None

        exchange = self.exchanges[exchange_name]
        
        try:
            # Attempt to place a market order
            order_side = signal.side.lower()  # CCXT expects lowercase
            order = await exchange.create_market_order(
                symbol=signal.symbol,
                side=order_side,
                amount=amount_usdt,
            )
            
            # Log order details on success
            order_id = order.get("id", "N/A")
            filled_price = order.get("average", order.get("price", "N/A"))
            filled_amount = order.get("filled", order.get("amount", amount_usdt))
            
            logger.info(
                f"Order placed successfully on {exchange_name}: "
                f"ID={order_id}, Symbol={signal.symbol}, Side={signal.side}, "
                f"Amount={filled_amount}, Price={filled_price}"
            )
            
            return order
            
        except ccxt.NetworkError as e:
            # Handle network/connection errors - attempt reconnection
            logger.error(
                f"Network error on {exchange_name} while placing order: {e}. "
                f"Attempting to reconnect..."
            )
            await self._reconnect_exchange(exchange_name)
            return None
            
        except ccxt.ExchangeError as e:
            # Handle exchange-specific errors (insufficient funds, invalid symbol, etc.)
            logger.error(
                f"Exchange error on {exchange_name} while placing order: {e} "
                f"(symbol: {signal.symbol}, side: {signal.side})"
            )
            return None
            
        except Exception as e:
            # Catch all other exceptions to prevent crashing
            logger.error(
                f"Unexpected error on {exchange_name} while placing order: {e} "
                f"(symbol: {signal.symbol}, side: {signal.side})"
            )
            return None

    async def _reconnect_exchange(self, exchange_name: str) -> bool:
        """Attempt to reconnect to a disconnected exchange.
        
        Args:
            exchange_name: The name of the exchange to reconnect.
            
        Returns:
            True if reconnection was successful, False otherwise.
        """
        if exchange_name not in self.exchanges:
            logger.warning(f"Cannot reconnect: exchange '{exchange_name}' not found.")
            return False

        exchange = self.exchanges[exchange_name]
        
        try:
            # Test connection by fetching server time or markets
            await exchange.load_markets(reload=True)
            logger.info(f"Successfully reconnected to {exchange_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to {exchange_name}: {e}")
            return False
