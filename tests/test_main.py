"""Tests for src/main.py – JS loading and injection logic."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from src.main import inject_observer, load_observer_js


class TestLoadObserverJs:
    """Tests for the load_observer_js helper function."""

    def test_loads_observer_js_successfully(self):
        """load_observer_js returns the content of js/observer.js."""
        content = load_observer_js()
        assert isinstance(content, str)
        assert len(content) > 0

    def test_content_contains_mutation_observer(self):
        """The loaded JS should contain MutationObserver setup code."""
        content = load_observer_js()
        assert "MutationObserver" in content

    def test_content_contains_discord_message_type(self):
        """The loaded JS should output DISCORD_MESSAGE typed JSON."""
        content = load_observer_js()
        assert "DISCORD_MESSAGE" in content

    def test_raises_file_not_found_when_missing(self):
        """load_observer_js raises FileNotFoundError when observer.js is missing."""
        with patch("builtins.open", side_effect=FileNotFoundError("No such file")):
            with pytest.raises(FileNotFoundError):
                load_observer_js()


class TestInjectObserver:
    """Tests for the async inject_observer function."""

    @pytest.mark.asyncio
    async def test_successful_injection(self, caplog):
        """inject_observer calls page.evaluate with JS code and logs success."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        with caplog.at_level(logging.INFO):
            await inject_observer(mock_page)

        # page.evaluate should have been called once with the JS content
        mock_page.evaluate.assert_called_once()
        js_arg = mock_page.evaluate.call_args[0][0]
        assert isinstance(js_arg, str)
        assert "MutationObserver" in js_arg

        # Success log message
        assert "MutationObserver 注入成功" in caplog.text

    @pytest.mark.asyncio
    async def test_injection_failure_raises_runtime_error(self, caplog):
        """inject_observer raises RuntimeError when page.evaluate fails."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("Page crashed"))

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError, match="MutationObserver 注入失敗"):
                await inject_observer(mock_page)

        # Error should be logged
        assert "MutationObserver 注入失敗" in caplog.text
        assert "Page crashed" in caplog.text

    @pytest.mark.asyncio
    async def test_runtime_error_contains_retry_suggestion(self):
        """The RuntimeError message should include a retry suggestion."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("timeout"))

        with pytest.raises(RuntimeError) as exc_info:
            await inject_observer(mock_page)

        error_msg = str(exc_info.value)
        assert "建議" in error_msg
        assert "重試" in error_msg

    @pytest.mark.asyncio
    async def test_runtime_error_chains_original_exception(self):
        """The RuntimeError should chain the original exception via __cause__."""
        original_error = ValueError("evaluate failed")
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=original_error)

        with pytest.raises(RuntimeError) as exc_info:
            await inject_observer(mock_page)

        assert exc_info.value.__cause__ is original_error

    @pytest.mark.asyncio
    async def test_injection_loads_actual_js_file(self):
        """inject_observer loads and injects the real observer.js file content."""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        await inject_observer(mock_page)

        # Verify the injected code matches the actual file content
        expected_content = load_observer_js()
        actual_content = mock_page.evaluate.call_args[0][0]
        assert actual_content == expected_content
