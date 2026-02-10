# 實作計畫：Discord 訊息監聽與自動交易工具

## 概述

依據設計文件，將系統拆分為漸進式的實作任務。每個任務建立在前一個任務之上，確保程式碼始終可運行。使用 Python + Playwright + CCXT + Hypothesis 技術棧。

## 任務

- [x] 1. 建立專案結構與資料模型
  - [x] 1.1 建立專案目錄結構與依賴管理
    - 建立 `src/` 目錄結構：`config_manager.py`、`console_interceptor.py`、`channel_filter.py`、`trading_agent.py`、`exchange_client.py`、`main.py`
    - 建立 `tests/` 目錄與 `conftest.py`
    - 建立 `requirements.txt`，包含 `playwright`、`pyyaml`、`ccxt`、`hypothesis`、`pytest`、`pytest-asyncio`、`openai` 依賴
    - 建立 `js/observer.js` 存放注入腳本
    - _Requirements: 全域_

  - [x] 1.2 實作核心資料模型（DiscordMessage、TradeSignal、AppConfig）
    - 在 `src/models.py` 中定義 `DiscordMessage`、`TradeSignal`、`ExchangeConfig`、`TradingConfig`、`AppConfig` dataclass
    - 實作 `DiscordMessage` 的 `to_json()` 和 `from_json()` 方法
    - 實作 `TradeSignal` 的驗證方法（`validate()`），確保 side 為 BUY/SELL、confidence 為 0-100
    - _Requirements: 6.1, 6.2, 6.3, 7.4_

  - [ ]* 1.3 撰寫 DiscordMessage 序列化往返 property test
    - **Property 2: 訊息序列化往返一致性（Round-Trip）**
    - 使用 Hypothesis 生成隨機 DiscordMessage，驗證 `from_json(to_json(msg)) == msg`
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [ ]* 1.4 撰寫 TradeSignal 結構不變量 property test
    - **Property 4: TradeSignal 結構不變量**
    - 使用 Hypothesis 生成隨機 TradeSignal，驗證所有欄位約束
    - **Validates: Requirements 7.3, 7.4**

- [x] 2. 實作設定檔管理
  - [x] 2.1 實作 ConfigManager
    - 在 `src/config_manager.py` 中實作 `ConfigManager` 類別
    - 實作 `load()` 方法：從 YAML 檔案載入設定並轉換為 `AppConfig`
    - 實作 `validate()` 方法：驗證所有欄位（交易所名稱、API Key、閾值範圍等）
    - 實作 `generate_default()` 方法：產生包含預設值和註解的範例 YAML 設定檔
    - 實作 `save()` 方法：將 `AppConfig` 寫回 YAML 檔案（供 property test 使用）
    - 當設定檔不存在時自動呼叫 `generate_default()`
    - 當設定檔格式錯誤時回傳明確的錯誤訊息清單
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 11.5_

  - [ ]* 2.2 撰寫設定檔往返 property test
    - **Property 7: 設定檔載入往返一致性**
    - 使用 Hypothesis 生成隨機 AppConfig，驗證 `load(save(config)) == config`
    - **Validates: Requirements 9.1**

  - [ ]* 2.3 撰寫格式錯誤設定檔 property test
    - **Property 8: 格式錯誤的設定檔產生錯誤訊息**
    - 使用 Hypothesis 生成格式錯誤的 YAML 字串，驗證 `load()` 回傳非空錯誤清單且不拋出例外
    - **Validates: Requirements 9.4**

  - [ ]* 2.4 撰寫設定檔單元測試
    - 測試設定檔不存在時產生範例檔案（需求 9.3）
    - 測試預設 `read_only_mode` 為 `true`（需求 11.1, 11.5）
    - 測試設定檔包含所有必要區塊（需求 9.2）
    - _Requirements: 9.2, 9.3, 11.1, 11.5_

- [x] 3. 實作頻道篩選與 Console 攔截
  - [x] 3.1 實作 ChannelFilter
    - 在 `src/channel_filter.py` 中實作 `ChannelFilter` 類別
    - 實作 `should_process()` 方法：比對頻道名稱是否在目標清單中
    - 實作 `filter_message()` 方法：篩選 DiscordMessage
    - 當目標清單為空時記錄警告並回傳 False
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 3.2 撰寫頻道篩選 property test
    - **Property 1: 頻道篩選正確性**
    - 使用 Hypothesis 生成隨機頻道名稱和清單，驗證 `should_process()` 的若且唯若語義
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.6**

  - [x] 3.3 實作 ConsoleInterceptor
    - 在 `src/console_interceptor.py` 中實作 `ConsoleInterceptor` 類別
    - 實作 `parse_message()` 靜態方法：解析 JSON 字串為 DiscordMessage，無效格式回傳 None
    - 實作 `serialize_message()` 靜態方法：序列化 DiscordMessage 為 JSON
    - 實作 `handle_console()` 方法：處理 Playwright ConsoleMessage 事件，有效訊息觸發 callback
    - 在終端機以格式化方式印出訊息（發送者、內容、時間、頻道）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2_

  - [ ]* 3.4 撰寫無效 Console Log 處理 property test
    - **Property 3: 無效 Console Log 的優雅處理**
    - 使用 Hypothesis 生成隨機非 JSON 字串，驗證 `parse_message()` 回傳 None 且不拋出例外
    - **Validates: Requirements 5.4**

- [x] 4. Checkpoint - 確認核心元件測試通過
  - 確認所有測試通過，如有問題請告知。

- [x] 5. 實作 MutationObserver 注入腳本
  - [x] 5.1 撰寫 JavaScript MutationObserver 注入腳本
    - 在 `js/observer.js` 中實作完整的注入腳本
    - 使用語義化 selector（`[role="list"][data-list-id="chat-messages"]`、`[role="article"]`）定位 DOM 元素
    - 實作 `extractAndLog()` 函式：從 article 節點擷取 author、content、timestamp、channel
    - 以 `console.log(JSON.stringify({type: "DISCORD_MESSAGE", ...}))` 輸出
    - 實作捲動位置鎖定邏輯（每 5 秒檢查，低頻率）
    - 處理 DOM 節點不含預期結構的情況（靜默跳過）
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 10.4, 11.4_

  - [x] 5.2 在 `src/main.py` 中實作 JS 腳本載入與注入邏輯
    - 讀取 `js/observer.js` 檔案內容
    - 透過 `page.evaluate()` 注入至 Discord 頁面
    - 處理注入失敗的錯誤（顯示原因並建議重試）
    - _Requirements: 4.1, 10.2_

- [ ] 6. 實作 Trading Agent
  - [ ] 6.1 實作 TradingAgent
    - 在 `src/trading_agent.py` 中實作 `TradingAgent` 類別
    - 實作 `_build_prompt()` 方法：建構 LLM 分析 prompt，要求回傳 JSON 格式的交易信號
    - 實作 `_parse_response()` 方法：解析 LLM 回應為 TradeSignal，無法解析時回傳 None
    - 實作 `analyze()` 非同步方法：呼叫 LLM API 分析訊息，產生 TradeSignal 或 None
    - 在終端機印出每次分析的總結資訊
    - 捕獲所有 LLM API 錯誤，記錄後回傳 None
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 10.5_

- [ ] 7. 實作交易所下單整合
  - [~] 7.1 實作 ExchangeClient
    - 在 `src/exchange_client.py` 中實作 `ExchangeClient` 類別
    - 實作 `_init_exchanges()` 方法：使用 CCXT 初始化 Binance、Bybit、MEXC 連線
    - 實作 `_check_confidence()` 方法：檢查信心度是否達到閾值
    - 實作 `_check_amount_limit()` 方法：檢查交易金額是否在限制內
    - 實作 `place_order()` 非同步方法：執行下單，記錄訂單詳情或錯誤
    - 下單失敗時捕獲例外並記錄，不中斷主程式
    - 交易所斷線時嘗試重新連線
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.6_

  - [ ]* 7.2 撰寫信心度閾值 property test
    - **Property 5: 信心度閾值門檻控制**
    - 使用 Hypothesis 生成隨機 confidence 和 threshold，驗證 `_check_confidence()` 行為
    - **Validates: Requirements 8.6**

  - [ ]* 7.3 撰寫交易金額上限 property test
    - **Property 6: 交易金額上限控制**
    - 使用 Hypothesis 生成隨機金額和上限，驗證 `_check_amount_limit()` 行為
    - **Validates: Requirements 8.7**

  - [ ]* 7.4 撰寫交易所單元測試
    - 測試支援的交易所清單包含 Binance、Bybit、MEXC（需求 8.1）
    - 測試下單失敗不中斷主程式（需求 8.5，使用 mock）
    - _Requirements: 8.1, 8.5_

- [ ] 8. 實作 Batch Launcher 與主程式串接
  - [~] 8.1 建立 Batch Launcher
    - 建立 `start_discord.bat`
    - 使用 `tasklist` 檢查 Discord 是否已在執行
    - 若已執行，顯示提示訊息並退出
    - 以 `--remote-debugging-port=9222` 參數啟動 Discord
    - 顯示 CDP 連線資訊
    - _Requirements: 1.1, 1.2, 1.3_

  - [~] 8.2 實作 ListenerScript 主程式
    - 在 `src/main.py` 中實作 `ListenerScript` 類別
    - 實作 `start()` 方法：載入設定 → 顯示風險提示 → 連接 CDP → 注入 Observer → 監聽迴圈
    - 實作 `_show_risk_warning()` 方法：顯示 CDP 連接 Discord 的風險提示
    - 實作 `_connect_cdp()` 方法：使用 Playwright `connect_over_cdp`，30 秒逾時
    - 實作 `_on_message()` callback：串接 Channel_Filter → Trading_Agent → Exchange_Client
    - 實作 `shutdown()` 方法：優雅關閉所有連線
    - 註冊 SIGINT 信號處理（Ctrl+C）
    - 在 read_only_mode 下跳過交易所下單
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.5, 10.1, 10.3, 11.1, 11.2, 11.3_

  - [ ]* 8.3 撰寫主程式單元測試
    - 測試風險提示訊息包含關鍵警告文字（需求 11.2）
    - 測試 CDP 連線逾時設定為 30 秒（需求 2.4）
    - _Requirements: 2.4, 11.2_

- [ ] 9. 最終 Checkpoint - 確認所有測試通過
  - 確認所有測試通過，如有問題請告知。

## 備註

- 標記 `*` 的任務為選擇性任務，可跳過以加速 MVP 開發
- 每個任務都引用了對應的需求編號以確保可追溯性
- Checkpoint 任務用於確保漸進式驗證
- Property tests 使用 Hypothesis 框架，每個 property 至少 100 次迭代
- 單元測試驗證特定範例和邊界情況
