# 需求文件

## 簡介

本功能是一個 Python 工具，用於監聽 Discord 桌面應用程式中特定虛擬貨幣交易頻道的即時訊息。透過 Discord (Electron) 內建的 `--remote-debugging-port=9222` 功能，使用 Python 的 Playwright 套件連接 Chrome DevTools Protocol (CDP)，在 Discord 頁面中注入 JavaScript MutationObserver 來偵測聊天列表的 DOM 變動，擷取新訊息後交由 AI Agent 進行交易策略分析（多空判斷、總結），最終根據分析結果呼叫虛擬貨幣交易所 API（Binance、Bybit、MEXC）進行自動下單。

## 詞彙表

- **Discord_App**: Discord 桌面應用程式，基於 Electron 框架建構
- **CDP_Port**: Chrome DevTools Protocol 遠端除錯埠，預設為 9222
- **Listener_Script**: 使用 Python Playwright 撰寫的主要監聽腳本
- **Batch_Launcher**: 用於以 Debug 模式啟動 Discord 的 Windows Batch 檔案
- **MutationObserver_Injector**: 注入至 Discord 頁面的 JavaScript 程式碼，負責偵測 DOM 變動
- **Message_Extractor**: 從 DOM 變動中擷取新訊息文字內容的邏輯元件
- **Console_Interceptor**: 攔截瀏覽器 Console Log 事件並將訊息傳回 Python 的元件
- **Channel_Filter**: 負責篩選特定 Discord 頻道的元件，僅處理使用者設定的目標頻道訊息
- **Trading_Agent**: AI Agent 元件，負責分析訊息內容並產生交易策略（多空方向、信心度、總結）
- **Exchange_Client**: 與虛擬貨幣交易所 API 互動的客戶端元件，支援 Binance、Bybit、MEXC
- **Trade_Signal**: Trading_Agent 產生的交易信號資料結構，包含交易方向、幣種、數量等資訊
- **Channel_Config**: 使用者設定的目標頻道清單，定義要監聽的頻道名稱或 ID

## 需求

### 需求 1：以 Debug 模式啟動 Discord

**使用者故事：** 身為使用者，我希望能透過一個 Batch 檔案以遠端除錯模式啟動 Discord，以便 Python 腳本能夠連接。

#### 驗收條件

1. THE Batch_Launcher SHALL 啟動 Discord_App 並附帶 `--remote-debugging-port=9222` 參數
2. WHEN Discord_App 已在執行中，THE Batch_Launcher SHALL 顯示提示訊息告知使用者需先關閉 Discord
3. WHEN Discord_App 成功啟動，THE Batch_Launcher SHALL 在終端機顯示 CDP_Port 的連線資訊

### 需求 2：連接 Discord CDP Port

**使用者故事：** 身為使用者，我希望 Python 腳本能自動連接到已開啟的 Discord 除錯埠，以便進行後續的訊息監聽。

#### 驗收條件

1. WHEN Listener_Script 啟動時，THE Listener_Script SHALL 使用 Playwright 的 CDP 連線功能連接至 `http://localhost:9222`
2. WHEN CDP_Port 無法連線，THE Listener_Script SHALL 顯示明確的錯誤訊息並提示使用者確認 Discord 是否已以 Debug 模式啟動
3. WHEN 成功連接 CDP_Port，THE Listener_Script SHALL 取得 Discord 的主要頁面物件以供後續操作
4. IF 連線過程中發生逾時，THEN THE Listener_Script SHALL 在 30 秒後終止嘗試並顯示逾時錯誤訊息

### 需求 3：頻道篩選與監聽

**使用者故事：** 身為使用者，我希望能指定要監聽的特定 Discord 頻道，以便只接收我關注的虛擬貨幣交易頻道訊息。

#### 驗收條件

1. THE Channel_Filter SHALL 從設定檔讀取使用者指定的目標頻道清單（Channel_Config）
2. WHEN 收到新訊息時，THE Channel_Filter SHALL 比對訊息來源頻道是否在目標頻道清單中
3. WHEN 訊息來源頻道在目標清單中，THE Channel_Filter SHALL 將訊息傳遞給後續處理流程
4. WHEN 訊息來源頻道不在目標清單中，THE Channel_Filter SHALL 忽略該訊息
5. THE Channel_Config SHALL 支援以頻道名稱作為篩選條件
6. WHEN 目標頻道清單為空，THE Channel_Filter SHALL 記錄警告訊息並不處理任何訊息

### 需求 4：注入 JavaScript MutationObserver

**使用者故事：** 身為使用者，我希望腳本能在 Discord 頁面中注入監聽程式碼，以便偵測聊天列表的變動。

#### 驗收條件

1. WHEN 成功取得 Discord 頁面物件，THE MutationObserver_Injector SHALL 在頁面中注入 JavaScript 程式碼以建立 MutationObserver
2. THE MutationObserver_Injector SHALL 監聽 Discord 聊天列表容器的 `childList` 和 `subtree` 變動
3. WHEN MutationObserver 偵測到新增的 DOM 節點，THE Message_Extractor SHALL 從新節點中擷取訊息的文字內容
4. THE Message_Extractor SHALL 擷取每則訊息的發送者名稱、訊息內容、時間戳記及來源頻道名稱
5. WHEN 擷取到新訊息資料，THE MutationObserver_Injector SHALL 透過 `console.log` 以 JSON 格式輸出訊息資料
6. THE MutationObserver_Injector SHALL 優先使用穩定的 DOM 屬性（如 `role="article"`、`aria-label`、`data-list-id` 等語義化屬性）作為 Selector，避免依賴 Discord 經 Hash 混淆的 Class Name（如 `message-2qnXI6`），以提升跨版本更新的穩定性
7. THE MutationObserver_Injector SHALL 在注入時確保聊天視窗的捲動位置鎖定在最底部，以應對 Discord 的虛擬滾動（Virtual Scrolling）機制，確保最新訊息的 DOM 節點始終被渲染
8. IF 聊天視窗的捲動位置偏離底部，THEN THE MutationObserver_Injector SHALL 自動將捲動位置重新定位至底部以避免遺漏新訊息

### 需求 5：攔截 Console Log 並輸出訊息

**使用者故事：** 身為使用者，我希望 Python 腳本能攔截瀏覽器的 Console Log，並將新訊息即時傳遞給後續處理流程。

#### 驗收條件

1. THE Console_Interceptor SHALL 監聽 Discord 頁面的所有 `console` 事件
2. WHEN 收到包含訊息資料的 Console Log，THE Console_Interceptor SHALL 解析 JSON 格式的訊息資料
3. WHEN 成功解析訊息資料，THE Listener_Script SHALL 在終端機以格式化方式印出發送者名稱、訊息內容、時間戳記及來源頻道
4. IF Console Log 的內容不是有效的訊息 JSON 資料，THEN THE Console_Interceptor SHALL 忽略該筆 Log 而不產生錯誤
5. THE Console_Interceptor SHALL 持續監聽直到使用者手動中斷程式（Ctrl+C）

### 需求 6：訊息資料的序列化與解析

**使用者故事：** 身為開發者，我希望訊息資料在 JavaScript 與 Python 之間以結構化的 JSON 格式傳遞，以確保資料的完整性與可解析性。

#### 驗收條件

1. THE MutationObserver_Injector SHALL 將訊息資料序列化為包含 `author`、`content`、`timestamp`、`channel` 欄位的 JSON 字串
2. THE Console_Interceptor SHALL 將接收到的 JSON 字串反序列化為 Python 字典物件
3. FOR ALL 有效的訊息資料物件，序列化後再反序列化 SHALL 產生與原始資料等價的物件（往返一致性）

### 需求 7：AI Agent 交易策略分析

**使用者故事：** 身為交易者，我希望 AI Agent 能分析 Discord 頻道中的訊息內容，判斷交易策略（多空方向），並產生交易信號。

#### 驗收條件

1. WHEN Channel_Filter 傳遞新訊息給 Trading_Agent，THE Trading_Agent SHALL 分析訊息內容以判斷交易相關資訊
2. THE Trading_Agent SHALL 從訊息中識別幣種（如 BTC、ETH）、交易方向（做多/做空）及相關價格資訊
3. WHEN Trading_Agent 完成分析，THE Trading_Agent SHALL 產生包含交易方向、幣種、信心度及分析總結的 Trade_Signal
4. THE Trade_Signal SHALL 包含以下欄位：`symbol`（幣種）、`side`（BUY/SELL）、`confidence`（0-100 信心度）、`summary`（分析總結）
5. WHEN Trading_Agent 無法從訊息中判斷明確的交易信號，THE Trading_Agent SHALL 記錄分析結果但不產生 Trade_Signal
6. THE Trading_Agent SHALL 在終端機印出每次分析的總結資訊

### 需求 8：交易所下單整合

**使用者故事：** 身為交易者，我希望系統能根據 AI Agent 的分析結果，自動在虛擬貨幣交易所下單。

#### 驗收條件

1. THE Exchange_Client SHALL 支援連接 Binance、Bybit、MEXC 三個交易所的 API
2. WHEN 收到有效的 Trade_Signal，THE Exchange_Client SHALL 根據信號內容在指定交易所建立訂單
3. THE Exchange_Client SHALL 從設定檔讀取各交易所的 API Key 和 Secret
4. WHEN 下單成功，THE Exchange_Client SHALL 記錄訂單詳情（訂單 ID、幣種、方向、數量、價格）
5. IF 下單失敗，THEN THE Exchange_Client SHALL 記錄錯誤原因並不中斷主程式運行
6. WHEN Trade_Signal 的信心度低於設定的閾值，THE Exchange_Client SHALL 跳過下單並記錄原因
7. THE Exchange_Client SHALL 支援設定每筆交易的最大金額限制以控制風險

### 需求 9：設定檔管理

**使用者故事：** 身為使用者，我希望能透過設定檔管理所有可配置的參數，以便靈活調整工具的行為。

#### 驗收條件

1. THE Listener_Script SHALL 從 YAML 或 JSON 設定檔讀取所有可配置參數
2. THE 設定檔 SHALL 包含以下區塊：目標頻道清單、交易所 API 憑證、Trading_Agent 參數、風險控制參數
3. WHEN 設定檔不存在，THE Listener_Script SHALL 產生包含預設值的範例設定檔
4. WHEN 設定檔格式錯誤，THE Listener_Script SHALL 顯示明確的錯誤訊息指出問題所在
5. THE 設定檔 SHALL 支援設定信心度閾值、最大交易金額、啟用的交易所清單

### 需求 10：錯誤處理與穩定性

**使用者故事：** 身為使用者，我希望工具在遇到錯誤時能優雅地處理，而不是直接崩潰。

#### 驗收條件

1. IF Discord_App 在監聽過程中被關閉，THEN THE Listener_Script SHALL 偵測到連線中斷並顯示適當的錯誤訊息後安全退出
2. IF MutationObserver_Injector 注入失敗，THEN THE Listener_Script SHALL 顯示錯誤原因並提供重試建議
3. WHEN 使用者按下 Ctrl+C，THE Listener_Script SHALL 優雅地關閉所有連線並釋放資源後退出
4. IF 擷取到的 DOM 節點不包含預期的訊息結構，THEN THE Message_Extractor SHALL 跳過該節點並繼續監聽
5. IF Trading_Agent 分析過程中發生錯誤，THEN THE Listener_Script SHALL 記錄錯誤並繼續監聽新訊息
6. IF Exchange_Client 與交易所的連線中斷，THEN THE Exchange_Client SHALL 嘗試重新連線並記錄連線狀態

### 需求 11：風控與合規注意事項

**使用者故事：** 身為使用者，我希望工具在設計上優先考慮帳號安全與合規性，降低被 Discord 偵測或封禁的風險。

#### 驗收條件

1. THE Listener_Script SHALL 預設以「只讀模式」運行，僅讀取 DOM 訊息資料，不透過 CDP 自動發送任何訊息或執行任何模擬使用者操作（如點擊、輸入）
2. THE Listener_Script SHALL 在啟動時於終端機顯示風險提示，告知使用者此工具透過 CDP 連接 Discord 可能違反 Discord 服務條款（ToS），使用者需自行承擔風險
3. IF 使用者啟用自動下單功能，THEN THE Listener_Script SHALL 僅透過交易所 API 執行交易操作，絕不透過 Discord 介面進行任何寫入操作
4. THE Listener_Script SHALL 避免以異常頻率存取 DOM（例如不應以高於每秒一次的頻率主動輪詢），以降低被 Client 端偵測的風險
5. THE 設定檔 SHALL 包含 `read_only_mode` 參數（預設為 `true`），明確控制工具是否僅以只讀模式運行
