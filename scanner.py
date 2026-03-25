#!/usr/bin/env python3
"""
scanner.py — scan all configured pairs and surface actionable signals
Usage:
    python scanner.py
"""

from datetime import datetime, timezone
from pathlib import Path
import csv

from data.fetcher import MarketDataFetcher
from indicators.trend import add_ema
from indicators.momentum import add_rsi
from indicators.volatility import add_atr
from strategies.multi_tf import MultiTimeframeStrategy
from config.settings import (
    DEFAULT_LIMIT, MIN_CONFIDENCE, EMA_SPREAD_THRESHOLD,
    ATR_SL_MULTIPLIER, RR_RATIO
)

# ── Pair registry ─────────────────────────────────────────────────────────────

PAIRS = [
    # Forex majors
    {"symbol": "EURUSD=X", "asset_type": "forex", "group": "Major"},
    {"symbol": "GBPUSD=X", "asset_type": "forex", "group": "Major"},
    {"symbol": "USDJPY=X", "asset_type": "forex", "group": "Major"},
    {"symbol": "AUDUSD=X", "asset_type": "forex", "group": "Major"},
    # Forex minors
    {"symbol": "EURGBP=X", "asset_type": "forex", "group": "Minor"},
    {"symbol": "EURJPY=X", "asset_type": "forex", "group": "Minor"},
    {"symbol": "GBPJPY=X", "asset_type": "forex", "group": "Minor"},
    # Crypto
    {"symbol": "BTC/USDT", "asset_type": "crypto", "group": "Crypto"},
    {"symbol": "ETH/USDT", "asset_type": "crypto", "group": "Crypto"},
    # Commodities
    {"symbol": "GC=F",     "asset_type": "forex",  "group": "Commodity"},  # Gold
    {"symbol": "CL=F",     "asset_type": "forex",  "group": "Commodity"},  # Oil
    {"symbol": "BZ=F",     "asset_type": "forex",  "group": "Commodity"},  # Brent Crude Oil

]

TIMEFRAME = "1h"
HTF       = "4h"
LIMIT     = DEFAULT_LIMIT

SCAN_LOG  = Path("charts/scan_log.csv")

SCAN_FIELDS = [
    "timestamp", "pair", "group", "direction", "confidence",
    "entry", "sl", "tp", "rr_ratio", "htf_confirmation",
    "ema_spread", "rsi", "reasons"
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prepare(symbol, timeframe, asset_type):
    try:
        fetcher = MarketDataFetcher(asset_type=asset_type, use_cache=True)
        df = fetcher.fetch(symbol, timeframe, LIMIT)
        df = add_ema(df, 20)
        df = add_ema(df, 50)
        df = add_rsi(df)
        df = add_atr(df)
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to prepare {symbol} {timeframe}: {e}") from e


def _calc_levels(direction, entry, atr):
    sl_distance = atr * ATR_SL_MULTIPLIER
    if direction == "BUY":
        sl = round(entry - sl_distance, 6)
        tp = round(entry + sl_distance * RR_RATIO, 6)
    else:
        sl = round(entry + sl_distance, 6)
        tp = round(entry - sl_distance * RR_RATIO, 6)
    return sl, tp


def _htf_label(reasons):
    for r in reasons:
        if "STRONG" in r:
            return "STRONG"
        if "WEAK" in r:
            return "WEAK"
        if "no entry" in r.lower():
            return "NONE"
    return "—"


def _append_scan_log(rows):
    is_new = not SCAN_LOG.exists()
    SCAN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SCAN_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCAN_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def _print_signals(signals):
    print(f"  {'Pair':<12} {'Grp':<9} {'Dir':<5} {'Conf':<6} {'Entry':<12} {'SL':<12} {'TP':<12} {'RSI'}")
    print(f"  {'─'*80}")
    for r in signals:
        icon = "▲" if r["decision"] == "BUY" else "▼"
        print(
            f"  {r['symbol']:<12} {r['group']:<9} {icon} {r['decision']:<4} "
            f"{r['confidence']:<6} {str(r['entry']):<12} {str(r['sl']):<12} "
            f"{str(r['tp']):<12} {r['rsi']}"
        )
        for reason in r["reasons"]:
            print(f"    · {reason}")
        print()


# ── Core scan ─────────────────────────────────────────────────────────────────

def scan():
    # timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    strategy  = MultiTimeframeStrategy()

    results   = []   # all pairs
    actionable = []  # BUY/SELL only, for log

    print(f"\n{'═' * 70}")
    print(f"  MARKET SCANNER   {timestamp} UTC")
    print(f"{'═' * 70}")

    for pair in PAIRS:
        symbol     = pair["symbol"]
        asset_type = pair["asset_type"]
        group      = pair["group"]

        try:
            df_ltf = _prepare(symbol, TIMEFRAME, asset_type)
            df_htf = _prepare(symbol, HTF,       asset_type)
        except Exception as e:
            print(f"  ⚠️  {symbol:<12} — skipped ({e})")
            results.append({
                "symbol": symbol, "group": group,
                "decision": "ERROR", "confidence": 0,
                "entry": "—", "sl": "—", "tp": "—",
                "htf": "—", "ema_spread": "—",
                "rsi": "—", "reasons": [str(e)]
            })
            continue

        try:
            decision, reasons, confidence = strategy.apply(df_ltf, df_htf)
        except Exception as e:
            print(f"  ⚠️  {symbol:<12} — strategy error ({e})")
            continue

        latest     = df_ltf.iloc[-1]
        entry      = round(float(latest["close"]), 6)
        atr        = float(latest["atr"])
        rsi        = round(float(latest["rsi"]), 2)
        ema_spread = round(abs(float(latest["ema_20"]) - float(latest["ema_50"])), 6)
        htf_label  = _htf_label(reasons)

        # Apply same filters as live signal
        is_filtered = (
            decision in ("BUY", "SELL") and (
                confidence < MIN_CONFIDENCE or
                ema_spread < EMA_SPREAD_THRESHOLD
            )
        )

        if is_filtered:
            decision = "FILTERED"

        sl, tp = ("—", "—")
        if decision in ("BUY", "SELL") and htf_label == "STRONG":
            sl, tp = _calc_levels(decision, entry, atr)

        results.append({
            "symbol":     symbol,
            "group":      group,
            "decision":   decision,
            "confidence": confidence,
            "entry":      entry,
            "sl":         sl,
            "tp":         tp,
            "htf":        htf_label,
            "ema_spread": ema_spread,
            "rsi":        rsi,
            "reasons":    reasons,
        })

        if decision in ("BUY", "SELL"):
            actionable.append({
                "timestamp":        timestamp,
                "pair":             symbol,
                "group":            group,
                "direction":        decision,
                "confidence":       confidence,
                "entry":            entry,
                "sl":               sl,
                "tp":               tp,
                "rr_ratio":         RR_RATIO,
                "htf_confirmation": htf_label,
                "ema_spread":       ema_spread,
                "rsi":              rsi,
                "reasons":          " | ".join(reasons),
            })

    # ── Terminal output ───────────────────────────────────────────────────────

    # Actionable signals first
    buy_sell = [r for r in results if r["decision"] in ("BUY", "SELL")]
    filtered = [r for r in results if r["decision"] == "FILTERED"]
    hold     = [r for r in results if r["decision"] == "HOLD"]
    errors   = [r for r in results if r["decision"] == "ERROR"]

    if buy_sell:
        strong_signals = [r for r in buy_sell if r["htf"] == "STRONG"]
        weak_signals   = [r for r in buy_sell if r["htf"] != "STRONG"]

        if strong_signals:
            print(f"\n  ✅ STRONG SIGNALS  (HTF confirmed)")
            _print_signals(strong_signals)

        if weak_signals:
            print(f"\n  ⚠️  WEAK SIGNALS  (no HTF confirmation — display only)")
            _print_signals(weak_signals)

    else:
        print("\n  No actionable signals right now.")

    # Summary table — all pairs
    print(f"\n  {'ALL PAIRS SUMMARY':}")
    print(f"  {'Pair':<12} {'Group':<9} {'Decision':<10} {'Entry':<12} {'SL':<12} {'TP':<12} {'Conf':<6} {'RSI':<7} {'HTF'}")
    print(f"  {'─'*55}")

    for r in results:
        icon = (
            "▲ " if r["decision"] == "BUY"      else
            "▼ " if r["decision"] == "SELL"     else
            "⚡ " if r["decision"] == "FILTERED" else
            "—  "
        )
        print(
            f"  {r['symbol']:<12} {r['group']:<9} "
            f"{icon}{r['decision']:<8}  {str(r['entry']):<12} {str(r['sl']):<12} {str(r['tp']):<12} "
            f"{str(r['confidence']):<6} {str(r['rsi']):<7} {r['htf']}"
        )

    # Footer stats
    strong = [r for r in results if r["decision"] in ("BUY", "SELL") and r["htf"] == "STRONG"]
    print(f"\n  {'─'*65}")
    print(f"  Scanned : {len(results)} pairs   "
          f"Strong Signals : {len(strong)}   "
          f"Weak/Filtered : {len(buy_sell) - len(strong) + len(filtered)}   "
          f"Hold : {len(hold)}")
    print(f"  {'═'*65}\n")

    # ── CSV output ────────────────────────────────────────────────────────────
    if actionable:
        _append_scan_log(actionable)
        print(f"  📄 {len(actionable)} signal(s) saved → {SCAN_LOG}\n")

    return results


if __name__ == "__main__":
    scan()
