"""Main Listener Script module.

Entry point that orchestrates all components: CDP connection, observer injection,
message listening, AI analysis, and exchange order execution.
"""

import logging
import os


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
