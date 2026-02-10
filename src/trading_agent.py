"""Trading Agent module.

AI Agent that analyzes Discord messages and generates trade signals.
"""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from src.models import DiscordMessage, TradeSignal


logger = logging.getLogger(__name__)


class TradingAgent:
    """AI Agent that analyzes Discord messages for cryptocurrency trading signals.
    
    Uses OpenAI's API to analyze message content and generate TradeSignal objects
    containing trading direction, confidence level, and analysis summary.
    """

    def __init__(self, model: str, api_key: str):
        """Initialize the TradingAgent.
        
        Args:
            model: The OpenAI model to use (e.g., "gpt-4o-mini").
            api_key: The OpenAI API key for authentication.
        """
        self.model = model
        self.api_key = api_key
        self._client = AsyncOpenAI(api_key=api_key)

    def _build_prompt(self, message: DiscordMessage) -> str:
        """Build the LLM analysis prompt.
        
        Constructs a prompt that instructs the LLM to analyze the Discord message
        for cryptocurrency trading signals and return a JSON response.
        
        Args:
            message: The Discord message to analyze.
            
        Returns:
            A formatted prompt string for the LLM.
        """
        return f"""你是一個專業的加密貨幣交易分析師。請分析以下 Discord 訊息，判斷是否包含明確的交易信號。

訊息資訊：
- 發送者：{message.author}
- 頻道：{message.channel}
- 時間：{message.timestamp}
- 內容：{message.content}

請分析此訊息並判斷：
1. 是否包含明確的加密貨幣交易建議（做多/做空）
2. 涉及的幣種（如 BTC、ETH 等）
3. 交易方向（BUY 做多 或 SELL 做空）
4. 你對此信號的信心度（0-100）

如果訊息包含明確的交易信號，請以以下 JSON 格式回應：
{{
    "has_signal": true,
    "symbol": "幣種/USDT（例如：BTC/USDT）",
    "side": "BUY 或 SELL",
    "confidence": 信心度數字（0-100）,
    "summary": "簡短的分析總結"
}}

如果訊息不包含明確的交易信號（例如：閒聊、問題、不確定的觀點等），請回應：
{{
    "has_signal": false,
    "summary": "為什麼此訊息不包含明確交易信號的說明"
}}

請只回應 JSON，不要包含其他文字。"""

    def _parse_response(self, response: str) -> Optional[TradeSignal]:
        """Parse the LLM response into a TradeSignal.
        
        Attempts to parse the JSON response from the LLM and create a valid
        TradeSignal object. Returns None if parsing fails or the signal is invalid.
        
        Args:
            response: The raw response string from the LLM.
            
        Returns:
            A TradeSignal if the response contains a valid signal, None otherwise.
        """
        try:
            # Try to extract JSON from the response
            # Handle cases where the response might have markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            data = json.loads(cleaned_response)
            
            # Check if there's a valid signal
            if not data.get("has_signal", False):
                logger.info(f"No trading signal detected: {data.get('summary', 'No summary')}")
                return None
            
            # Extract required fields
            symbol = data.get("symbol", "")
            side = data.get("side", "")
            confidence = data.get("confidence", 0)
            summary = data.get("summary", "")
            
            # Ensure confidence is an integer
            if isinstance(confidence, float):
                confidence = int(confidence)
            
            # Create TradeSignal
            signal = TradeSignal(
                symbol=symbol,
                side=side,
                confidence=confidence,
                summary=summary
            )
            
            # Validate the signal
            errors = signal.validate()
            if errors:
                logger.warning(f"Invalid TradeSignal: {errors}")
                return None
            
            return signal
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return None
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to extract TradeSignal from response: {e}")
            return None

    async def analyze(self, message: DiscordMessage) -> Optional[TradeSignal]:
        """Analyze a Discord message and generate a trading signal.
        
        Calls the LLM API to analyze the message content and determine if it
        contains a valid trading signal. Prints analysis summary to terminal.
        
        Args:
            message: The Discord message to analyze.
            
        Returns:
            A TradeSignal if a valid signal is detected, None otherwise.
            Returns None and logs the error if any LLM API error occurs.
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(message)
            
            # Call the LLM API
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個專業的加密貨幣交易分析師，專門分析交易信號。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=500
            )
            
            # Extract the response content
            response_content = response.choices[0].message.content
            if response_content is None:
                logger.warning("LLM returned empty response")
                print(f"[TradingAgent] 分析完成 - 訊息來自 {message.author}@{message.channel}: LLM 回應為空")
                return None
            
            # Parse the response
            signal = self._parse_response(response_content)
            
            # Print analysis summary to terminal (Req 7.6)
            if signal:
                print(f"[TradingAgent] 分析完成 - 訊息來自 {message.author}@{message.channel}")
                print(f"  交易信號: {signal.side} {signal.symbol}")
                print(f"  信心度: {signal.confidence}%")
                print(f"  總結: {signal.summary}")
            else:
                print(f"[TradingAgent] 分析完成 - 訊息來自 {message.author}@{message.channel}: 無明確交易信號")
            
            return signal
            
        except APIConnectionError as e:
            logger.error(f"LLM API connection error: {e}")
            print(f"[TradingAgent] API 連線錯誤: {e}")
            return None
        except RateLimitError as e:
            logger.error(f"LLM API rate limit exceeded: {e}")
            print(f"[TradingAgent] API 速率限制: {e}")
            return None
        except APITimeoutError as e:
            logger.error(f"LLM API timeout: {e}")
            print(f"[TradingAgent] API 逾時: {e}")
            return None
        except APIError as e:
            logger.error(f"LLM API error: {e}")
            print(f"[TradingAgent] API 錯誤: {e}")
            return None
        except Exception as e:
            # Catch any other unexpected errors (Req 10.5)
            logger.error(f"Unexpected error during message analysis: {e}")
            print(f"[TradingAgent] 未預期的錯誤: {e}")
            return None
