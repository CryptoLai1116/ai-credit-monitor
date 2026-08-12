#!/usr/bin/env python3
"""每日自動更新 data/dashboard.json。

免費資料來源（不需 API key）：
- FRED fredgraph.csv：ICE BofA US Corporate OAS (BAMLC0A0CM)、BBB OAS (BAMLC0A4CBBB)
- Yahoo Finance chart API：ORCL / GOOGL / AMZN / META / QQQ 收盤價

只更新可驗證的量化欄位（OAS、股價 5 日變化、更新時間），
CDS 快照等需授權資料源的欄位維持人工更新。
"""
import json
import csv
import io
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "dashboard.json"

TST = timezone(timedelta(hours=8))

FRED_SERIES = {
    "corporate": "BAMLC0A0CM",   # ICE BofA US Corporate Index OAS (%)
    "bbb": "BAMLC0A4CBBB",       # ICE BofA BBB US Corporate Index OAS (%)
}

EQUITY_TICKERS = {
    "Oracle": "ORCL",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Meta": "META",
    "QQQ": "QQQ",
}


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-credit-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_fred(series_id: str):
    """回傳 [(date, value_bp), ...]，只保留有值的觀察日。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    rows = list(csv.reader(io.StringIO(http_get(url))))
    out = []
    for row in rows[1:]:
        if len(row) < 2 or row[1] in (".", ""):
            continue
        try:
            out.append((row[0], round(float(row[1]) * 100)))  # % -> bp
        except ValueError:
            continue
    return out


def fetch_yahoo_closes(symbol: str):
    """回傳最近一個月的 [(date, close), ...]（遞增排序）。"""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?range=1mo&interval=1d"
    )
    payload = json.loads(http_get(url))
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quotes = result["indicators"]["quote"][0].get("close", [])
    out = []
    for ts, close in zip(timestamps, quotes):
        if close is None:
            continue
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        out.append((date, float(close)))
    return out


def pct_change_5d(closes):
    """最近收盤 vs 5 個交易日前的百分比變化。"""
    if len(closes) < 6:
        return None
    latest = closes[-1][1]
    prior = closes[-6][1]
    return (latest / prior - 1.0) * 100


def fmt_pct(x):
    return f"{x:+.1f}%"


def short_date(iso: str) -> str:
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.month}/{d.day}"


def update_oas(data):
    labels = {"corporate": "ICE US Corporate OAS", "bbb": "ICE BBB OAS"}
    for key, series_id in FRED_SERIES.items():
        try:
            obs = fetch_fred(series_id)
        except Exception as e:
            print(f"[warn] FRED {series_id} 抓取失敗：{e}", file=sys.stderr)
            continue
        if len(obs) < 6:
            continue
        date, bp = obs[-1]
        prev_bp = obs[-6][1]
        delta = bp - prev_bp
        trend = "走擴" if delta > 2 else ("收窄" if delta < -2 else "穩定")
        for row in data.get("relativeTable", []):
            if row and row[0] == labels[key]:
                row[1] = f"{bp}bp ({short_date(date)})"
                row[2] = f"5日 {delta:+d}bp（{trend}）"
                row[3] = f"FRED {date}"
        print(f"[ok] {labels[key]}: {bp}bp ({date}), 5d {delta:+d}bp")


def update_divergence(data):
    closes = {}
    for name, sym in EQUITY_TICKERS.items():
        try:
            closes[name] = fetch_yahoo_closes(sym)
        except Exception as e:
            print(f"[warn] Yahoo {sym} 抓取失敗：{e}", file=sys.stderr)
    qqq_5d = pct_change_5d(closes.get("QQQ", []))
    for item in data.get("divergence", []):
        name = item.get("company")
        c = closes.get(name)
        eq_5d = pct_change_5d(c) if c else None
        if eq_5d is None:
            continue
        item["equity5d"] = fmt_pct(eq_5d)
        if qqq_5d is not None:
            item["relativeQQQ"] = fmt_pct(eq_5d - qqq_5d)
        # 依股價方向 + 既有 CDS 方向（人工欄位）重推 state / label
        cds = str(item.get("cds5d", ""))
        cds_up = cds.strip().startswith("+")
        eq_up = eq_5d >= 0
        if cds_up and eq_up:
            item["state"], item["label"] = "warning", "股漲、CDS 升"
        elif cds_up and not eq_up:
            item["state"], item["label"] = "riskoff", "股跌、CDS 升"
        elif not cds_up and eq_up:
            item["state"], item["label"] = "clean", "股漲、CDS 穩"
        else:
            item["state"], item["label"] = "warning", "股跌、CDS 穩"
        print(f"[ok] {name}: equity5d {item['equity5d']}, relQQQ {item.get('relativeQQQ')}")


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)

    update_oas(data)
    update_divergence(data)

    after = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if after == before:
        print("[info] 市場數據無變化，不更新檔案")
        return

    data["updatedAt"] = datetime.now(TST).strftime("%Y-%m-%d %H:%M TST（自動更新）")
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[done] 已更新 {DATA_FILE}")


if __name__ == "__main__":
    main()
