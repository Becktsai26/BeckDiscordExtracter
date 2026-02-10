"""Main Listener Script module.

Entry point that orchestrates all components: CDP connection, observer injection,
message listening, AI analysis, and exchange order execution.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright

from src.config_manager import ConfigManager
from src.channel_filter import ChannelFilter
from src.console_interceptor import ConsoleInterceptor
from src.trading_agent import TradingAgent
from src.exchange_client import ExchangeClient
from src.models import AppConfig, DiscordMessage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_observer_js() -> str:
    """Load the observer.js file content.

    Returns:
        The JavaScript source code as a string.

    Raises:
        FileNotFoundError: If the observer.js file does not exist.
    """
    js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "js", "observer.js")
    with open(js_path, "r", encoding="utf-8") as f:
        return f.read()


async def inject_observer(page) -> None:
    """Inject the MutationObserver JavaScript into the Discord page.

    Reads the observer.js file and evaluates it in the given Playwright page
    context. On success, logs an info message. On failure, logs the error
    and raises a RuntimeError with a retry suggestion.

    Args:
        page: A Playwright Page object.

    Raises:
        RuntimeError: If injection fails, with the original cause and a
            suggestion to retry after the Discord page has fully loaded.
    """
    try:
        js_code = load_observer_js()
        await page.evaluate(js_code)
        logging.info("MutationObserver 注入成功")
    except Exception as e:
        logging.error(f"MutationObserver 注入失敗: {e}")
        raise RuntimeError(
            f"MutationObserver 注入失敗: {e}\n"
            "建議：請確認 Discord 頁面已完全載入後重試。"
        ) from e


class ListenerScript:
    """Main orchestrator for the Discord message listener.
    
    Coordinates all components: configuration loading, CDP connection,
    observer injection, message filtering, AI analysis, and exchange orders.
    
    Attributes:
        config_manager: ConfigManager instance for loading configuration.
        config: The loaded AppConfig, or None if not yet loaded.
        running: Flag indicating whether the listener is running.
    """

    # CDP connection timeout in milliseconds (30 seconds as per Req 2.4)
    CDP_TIMEOUT_MS = 30000

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the ListenerScript.
        
        Args:
            config_path: Path to the YAML configuration file.
        """
        self.config_path = config_path
        self.config_manager = ConfigManager()
        self.config: Optional[AppConfig] = None
        self.running = False
        
        # Components initialized during start()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._channel_filter: Optional[ChannelFilter] = None
        self._trading_agent: Optional[TradingAgent] = None
        self._exchange_client: Optional[ExchangeClient] = None
        self._console_interceptor: Optional[ConsoleInterceptor] = None

    async def start(self) -> None:
        """Main startup flow.
        
        Executes the following steps:
        1. Load configuration file
        2. Display risk warning
        3. Connect to CDP
        4. Inject MutationObserver
        5. Set up console event listener
        6. Enter listening loop
        
        Raises:
            SystemExit: If configuration loading fails or CDP connection fails.
        """
        # Step 1: Load configuration
        logger.info("正在載入設定檔...")
        self.config, errors = self.config_manager.load(self.config_path)
        if errors:
            for error in errors:
                logger.error(f"設定檔錯誤: {error}")
            print("\n設定檔載入失敗，請檢查設定檔後重試。")
            sys.exit(1)
        
        logger.info("設定檔載入成功")
        
        # Step 2: Display risk warning
        self._show_risk_warning()
        
        # Step 3: Connect to CDP
        try:
            await self._connect_cdp()
        except Exception as e:
            logger.error(f"CDP 連線失敗: {e}")
            await self.shutdown()
            sys.exit(1)
        
        # Step 4: Initialize components
        self._channel_filter = ChannelFilter(self.config.target_channels)
        self._trading_agent = TradingAgent(
            model=self.config.llm_model,
            api_key=self.config.llm_api_key
        )
        self._exchange_client = ExchangeClient(
            exchanges_config=self.config.exchanges,
            trading_config=self.config.trading
        )
        self._console_interceptor = ConsoleInterceptor(on_message=self._on_message)
        
        # Step 5: Inject MutationObserver
        try:
            await inject_observer(self._page)
        except RuntimeError as e:
            logger.error(str(e))
            await self.shutdown()
            sys.exit(1)
        
        # Step 6: Set up console event listener
        self._page.on("console", self._console_interceptor.handle_console)
        
        # Set up disconnect detection (Req 10.1)
        self._page.on("close", self._on_page_close)
        
        # Register SIGINT handler (Ctrl+C) (Req 10.3)
        self._register_signal_handlers()
        
        # Enter listening loop (Req 5.5)
        self.running = True
        logger.info("開始監聽 Discord 訊息... (按 Ctrl+C 停止)")
        print("\n" + "=" * 50)
        print("監聽中... 按 Ctrl+C 停止")
        print("=" * 50 + "\n")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("監聽迴圈被取消")
        finally:
            await self.shutdown()

    def _show_risk_warning(self) -> None:
        """Display risk and compliance warning.
        
        Shows a warning message about the risks of using CDP to connect to Discord,
        including potential ToS violations. (Req 11.2)
        """
        warning_message = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                              ⚠️  風險提示  ⚠️                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  本工具透過 Chrome DevTools Protocol (CDP) 連接 Discord 桌面應用程式。       ║
║                                                                              ║
║  【重要警告】                                                                ║
║  • 此操作可能違反 Discord 服務條款 (Terms of Service)                        ║
║  • 使用本工具可能導致您的 Discord 帳號被暫停或永久封禁                       ║
║  • 您需自行承擔使用本工具的所有風險                                          ║
║                                                                              ║
║  【運行模式】                                                                ║
"""
        if self.config and self.config.read_only_mode:
            warning_message += "║  ✓ 目前為「只讀模式」- 僅監聽訊息，不執行任何交易                         ║\n"
        else:
            warning_message += "║  ⚠ 目前為「交易模式」- 將根據 AI 分析結果自動下單                          ║\n"
        
        warning_message += """║                                                                              ║
║  繼續使用即表示您已了解並接受上述風險。                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(warning_message)
        logger.warning("使用者已被告知 CDP 連接 Discord 的風險")

    async def _connect_cdp(self) -> None:
        """Connect to Discord via CDP using Playwright.
        
        Uses Playwright's connect_over_cdp with a 30-second timeout (Req 2.4).
        On failure, displays a clear error message suggesting the user check
        if Discord is running in debug mode (Req 2.2).
        
        Raises:
            RuntimeError: If CDP connection fails or times out.
        """
        logger.info(f"正在連接 CDP: {self.config.cdp_url}")
        
        try:
            self._playwright = await async_playwright().start()
            
            # Connect to CDP with 30 second timeout (Req 2.4)
            self._browser = await self._playwright.chromium.connect_over_cdp(
                self.config.cdp_url,
                timeout=self.CDP_TIMEOUT_MS
            )
            
            # Get the main Discord page (Req 2.3)
            contexts = self._browser.contexts
            if not contexts:
                raise RuntimeError("無法取得 Discord 瀏覽器上下文")
            
            pages = contexts[0].pages
            if not pages:
                raise RuntimeError("無法取得 Discord 頁面")
            
            self._page = pages[0]
            logger.info("CDP 連線成功")
            print(f"✓ 已成功連接至 Discord (CDP: {self.config.cdp_url})")
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for timeout error
            if "timeout" in error_msg.lower():
                raise RuntimeError(
                    f"CDP 連線逾時（超過 30 秒）\n"
                    f"請確認：\n"
                    f"  1. Discord 已以 Debug 模式啟動（使用 start_discord.bat）\n"
                    f"  2. CDP Port 9222 未被其他程式佔用\n"
                    f"  3. 防火牆未阻擋本地連線"
                ) from e
            
            # General connection error (Req 2.2)
            raise RuntimeError(
                f"CDP 連線失敗: {error_msg}\n"
                f"請確認 Discord 是否已以 Debug 模式啟動。\n"
                f"提示：執行 start_discord.bat 以正確模式啟動 Discord。"
            ) from e

    def _on_message(self, message: DiscordMessage) -> None:
        """Message processing callback.
        
        Processes incoming Discord messages through the pipeline:
        Channel_Filter → Trading_Agent → Exchange_Client
        
        In read_only_mode, skips exchange order placement (Req 11.1, 11.3).
        
        Args:
            message: The DiscordMessage received from the console interceptor.
        """
        # Step 1: Filter by channel
        filtered_message = self._channel_filter.filter_message(message)
        if filtered_message is None:
            logger.debug(f"訊息被頻道篩選器過濾: {message.channel}")
            return
        
        # Step 2: Analyze with Trading Agent (async, run in background)
        asyncio.create_task(self._process_message_async(filtered_message))

    async def _process_message_async(self, message: DiscordMessage) -> None:
        """Asynchronously process a filtered message.
        
        Analyzes the message with the Trading Agent and places orders if
        a valid signal is generated (unless in read_only_mode).
        
        Args:
            message: The filtered DiscordMessage to process.
        """
        try:
            # Analyze with Trading Agent
            signal = await self._trading_agent.analyze(message)
            
            if signal is None:
                return
            
            # Check read_only_mode (Req 11.1, 11.3)
            if self.config.read_only_mode:
                logger.info(
                    f"只讀模式：跳過下單 "
                    f"(信號: {signal.side} {signal.symbol}, 信心度: {signal.confidence}%)"
                )
                print(f"[只讀模式] 偵測到交易信號但不執行下單: {signal.side} {signal.symbol}")
                return
            
            # Place orders on enabled exchanges
            for exchange_name in self.config.trading.enabled_exchanges:
                try:
                    order = await self._exchange_client.place_order(
                        signal=signal,
                        exchange_name=exchange_name
                    )
                    if order:
                        print(f"[交易] 已在 {exchange_name} 下單: {signal.side} {signal.symbol}")
                except Exception as e:
                    logger.error(f"下單失敗 ({exchange_name}): {e}")
                    
        except Exception as e:
            # Catch all errors to prevent crashing (Req 10.5)
            logger.error(f"訊息處理錯誤: {e}")

    def _on_page_close(self) -> None:
        """Handle Discord page close event.
        
        Detects when Discord is closed and triggers a safe shutdown (Req 10.1).
        """
        logger.warning("Discord 頁面已關閉")
        print("\n⚠️  Discord 已斷線，正在安全退出...")
        self.running = False

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown.
        
        Registers SIGINT (Ctrl+C) handler for graceful shutdown (Req 10.3).
        """
        def signal_handler(sig, frame):
            logger.info("收到中斷信號，正在關閉...")
            print("\n收到中斷信號，正在優雅關閉...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Also handle SIGTERM on Unix systems
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown(self) -> None:
        """Gracefully shutdown all connections and release resources.
        
        Closes CDP connection, Playwright browser, and releases all resources.
        """
        logger.info("正在關閉連線...")
        self.running = False
        
        try:
            # Close the page
            if self._page:
                try:
                    # Remove event listeners to prevent callbacks during shutdown
                    self._page.remove_listener("console", self._console_interceptor.handle_console)
                    self._page.remove_listener("close", self._on_page_close)
                except Exception:
                    pass  # Ignore errors during cleanup
            
            # Close the browser connection
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.debug(f"關閉瀏覽器時發生錯誤: {e}")
            
            # Stop Playwright
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.debug(f"停止 Playwright 時發生錯誤: {e}")
            
            logger.info("所有連線已關閉")
            print("✓ 已安全關閉所有連線")
            
        except Exception as e:
            logger.error(f"關閉過程中發生錯誤: {e}")


async def main() -> None:
    """Main entry point for the Discord message listener.
    
    Creates a ListenerScript instance and starts the listening process.
    """
    listener = ListenerScript()
    await listener.start()


if __name__ == "__main__":
    asyncio.run(main())
