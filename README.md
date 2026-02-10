# Discord 訊息監聽與自動交易工具

透過 Chrome DevTools Protocol (CDP) 連接 Discord 桌面應用程式，監聽特定頻道的即時訊息，使用 AI 分析交易信號，並自動在加密貨幣交易所下單。

## ⚠️ 風險警告

- 此工具透過 CDP 連接 Discord，**可能違反 Discord 服務條款 (ToS)**
- 使用本工具可能導致您的 Discord 帳號被暫停或永久封禁
- 自動交易涉及財務風險，請謹慎使用
- **您需自行承擔使用本工具的所有風險**

## 功能特色

- 🔌 透過 CDP 連接 Discord 桌面應用程式
- 👀 使用 MutationObserver 監聽聊天 DOM 變動
- 🎯 支援指定特定頻道進行監聽
- 🤖 AI Agent 分析訊息內容，判斷交易信號
- 📈 支援 Binance、Bybit、MEXC 交易所自動下單
- 🔒 預設只讀模式，確保安全

## 系統需求

- Windows 10/11
- Python 3.10+
- Discord 桌面應用程式

## 安裝

1. 複製專案
```bash
git clone https://github.com/Becktsai26/BeckDiscordExtracter.git
cd BeckDiscordExtracter
```

2. 安裝依賴
```bash
pip install -r requirements.txt
playwright install chromium
```

## 使用方式

### 1. 啟動 Discord（Debug 模式）

執行 `start_discord.bat`，這會以 `--remote-debugging-port=9222` 參數啟動 Discord。

```batch
start_discord.bat
```

### 2. 設定 config.yaml

首次執行時會自動產生 `config.yaml` 範例檔，請根據需求修改：

```yaml
# CDP 連線位址
cdp_url: "http://localhost:9222"

# 只讀模式（預設 true，僅監聽不交易）
read_only_mode: true

# 目標頻道清單
target_channels:
  - "crypto-signals"
  - "trading-alerts"

# 交易所設定
exchanges:
  - name: "binance"
    api_key: "your-api-key"
    api_secret: "your-api-secret"
    enabled: false

# 交易參數
trading:
  confidence_threshold: 70
  max_trade_amount_usdt: 100.0
  enabled_exchanges:
    - "binance"

# LLM 設定
llm:
  model: "gpt-4o-mini"
  api_key: "your-openai-api-key"
```

### 3. 執行監聽腳本

```bash
python src/main.py
```

## 專案結構

```
├── src/
│   ├── main.py              # 主程式入口
│   ├── models.py            # 資料模型
│   ├── config_manager.py    # 設定檔管理
│   ├── channel_filter.py    # 頻道篩選
│   ├── console_interceptor.py # Console 事件攔截
│   ├── trading_agent.py     # AI 交易分析
│   └── exchange_client.py   # 交易所下單
├── js/
│   └── observer.js          # MutationObserver 注入腳本
├── tests/                   # 測試檔案
├── start_discord.bat        # Discord 啟動腳本
├── config.yaml              # 設定檔（自動產生）
└── requirements.txt         # Python 依賴
```

## 運作原理

1. **CDP 連接**：透過 Playwright 連接以 Debug 模式啟動的 Discord
2. **DOM 監聽**：注入 JavaScript MutationObserver 監聽聊天列表變動
3. **訊息擷取**：從 DOM 節點擷取訊息內容，透過 console.log 傳回 Python
4. **頻道篩選**：僅處理設定中指定的目標頻道訊息
5. **AI 分析**：使用 OpenAI API 分析訊息，判斷交易信號
6. **自動下單**：根據 AI 分析結果，透過 CCXT 在交易所下單

## 測試

```bash
pytest tests/ -v
```

## License

MIT
