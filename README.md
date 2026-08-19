# AI Credit Monitor

這是一個完整、可部署的靜態儀表板網站。

## 本地開啟

因為網站會讀取 `data/dashboard.json`，建議用本地 HTTP server：

```bash
python3 -m http.server 8000
```

然後開啟：

```text
http://localhost:8000
```

## 部署

可直接部署到：
- Vercel
- Netlify
- GitHub Pages
- Cloudflare Pages

不需要 build 指令，輸出目錄就是專案根目錄。

## 每日更新方式

網站資料放在：

```text
data/dashboard.json
```

每天更新該檔後重新部署，網站就會刷新。

## API 串接位置

目前前端從：

```text
data/dashboard.json
```

讀取資料。

之後可改成：

```javascript
fetch("https://your-api.example.com/dashboard")
```

## 重要限制

CDS、即時公司債 OAS、TRACE、新債訂單簿與 NIC 通常需要 Bloomberg、LSEG、ICE 或其他授權資料源。未串接授權 API 前，網站中的數值應視為研究框架或人工更新欄位。


## v2 新增功能
- Credit Regime 自動判讀
- Equity vs Credit Divergence


## v3 — CDS Snapshot Tracker

新增：
- `CDS Snapshots` 頁面
- Latest vs Previous 可驗證快照
- Δ bp / 間隔天數 / 資料新鮮度
- `data/cds_snapshot_schema.json`，供之後自動化或後端寫入
- Relative Credit Stress 改成對照「可驗證快照期間」的 Corporate / BBB OAS

### 部署到 Vercel
這是純靜態網站：
- Framework Preset: `Other`
- Build Command: 留空
- Output Directory: 留空
- Root Directory: `ai_credit_full_site`（如果你整個 zip 解壓後上傳）

網站目前仍以 `data/dashboard.json` 為前端資料來源；更新 JSON 後重新部署即可。


## v4 — AI Debt Duration Supply
新增 Duration Supply 頁面與首頁摘要：AI bond issuance、20Y+ share、duration-weighted supply、30Y AI bond NIC、AI vs peer excess spread、10Y/30Y Treasury、10Y/30Y real yield，以及 Saturation Test。
