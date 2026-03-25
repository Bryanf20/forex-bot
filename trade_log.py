#!/usr/bin/env python3
"""
trade_log.py — manually log test trades and results
Usage:
    python trade_log.py log     → add a new trade
    python trade_log.py results → update outcome of an existing trade
    python trade_log.py view    → print the log
"""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
import re

LOG_PATH = Path("charts/trade_log.csv")

FIELDS = [
    "id", "timestamp", "pair", "direction", "confidence",
    "entry", "sl", "tp", "rr_ratio", "atr",
    "ema_spread", "htf_confirmation", "signal_quality",
    "outcome", "exit_price", "pnl_pips", "pnl_pct", "duration_hrs",
    "notes"
]


def _read_all():
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, newline="") as f:
        return list(csv.DictReader(f))


def _write_all(rows):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _next_id(rows):
    return max((int(r["id"]) for r in rows), default=0) + 1


def _prompt(label, default=None):
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else (str(default) if default is not None else "")


def _calc_pnl(direction, entry, exit_price):
    entry, exit_price = float(entry), float(exit_price)
    if direction.upper() == "BUY":
        pnl_pct = (exit_price - entry) / entry * 100
    else:
        pnl_pct = (entry - exit_price) / entry * 100

    # pips: works for forex (5dp) and crypto (rounds naturally)
    pip_multiplier = 10000 if entry < 10 else 1
    if direction.upper() == "BUY":
        pnl_pips = (exit_price - entry) * pip_multiplier
    else:
        pnl_pips = (entry - exit_price) * pip_multiplier

    return round(pnl_pips, 1), round(pnl_pct, 4)

def _parse_last_signal(path="last_signal.txt"):
    """Parse signal values from saved terminal output."""
    if not Path(path).exists():
        return {}

    with open(path) as f:
        text = f.read()

    def find(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    pair      = find(r"pair\s+:\s+(\S+)")
    direction = find(r"decision\s+:\s+(BUY|SELL)")
    confidence= find(r"confidence\s+:\s+([0-9.]+)")
    entry     = find(r"entry\s+:\s+([0-9.]+)")
    sl        = find(r"sl\s+:\s+([0-9.]+)")
    tp        = find(r"tp\s+:\s+([0-9.]+)")
    rr        = "1:"+find(r"R:R\s+:\s+1:([0-9.]+)")
    # rr        = find(r"R:R\s*:\s*(1:\d+(\.\d+)?)")
    htf       = "STRONG" if "STRONG signal" in text else \
                "WEAK"   if "WEAK"          in text else "NONE"
    quality   = "STRONG" if "STRONG" in htf else "WEAK"

    # EMA spread from raw values
    ema20 = find(r"ema_20\s+:\s+([0-9.]+)")
    ema50 = find(r"ema_50\s+:\s+([0-9.]+)")
    spread = ""
    if ema20 and ema50:
        spread = str(round(abs(float(ema20) - float(ema50)), 6))

    return {
        "pair": pair, "direction": direction, "confidence": confidence,
        "entry": entry, "sl": sl, "tp": tp, "rr_ratio": rr or "2.0",
        "ema_spread": spread, "htf_confirmation": htf, "signal_quality": quality,
    }


def log_trade():
    rows  = _read_all()
    trade_id = _next_id(rows)
    parsed   = _parse_last_signal()   # ← load from last_signal.txt

    if parsed.get("pair"):
        print(f"\n  ✅ Signal detected from last_signal.txt — pre-filling values")

    print(f"\n── New Trade #{trade_id} ──────────────────────────────")
    pair       = _prompt("Pair",             default=parsed.get("pair"))
    direction  = _prompt("Direction",        default=parsed.get("direction", "")).upper()
    confidence = _prompt("Confidence",       default=parsed.get("confidence"))
    entry      = _prompt("Entry price",      default=parsed.get("entry"))
    sl         = _prompt("SL",               default=parsed.get("sl"))
    tp         = _prompt("TP",               default=parsed.get("tp"))
    rr_ratio   = _prompt("R:R ratio",        default=parsed.get("rr_ratio", "2.0"))
    atr        = _prompt("ATR (optional)")
    ema_spread = _prompt("EMA spread",       default=parsed.get("ema_spread"))
    htf        = _prompt("HTF confirmation", default=parsed.get("htf_confirmation", "NONE")).upper()
    quality    = _prompt("Signal quality",   default=parsed.get("signal_quality", "WEAK")).upper()
    notes      = _prompt("Notes (optional)")

    row = {
        "id": trade_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "pair": pair,
        "direction": direction,
        "confidence": confidence,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rr_ratio": rr_ratio,
        "atr": atr,
        "ema_spread": ema_spread,
        "htf_confirmation": htf,
        "signal_quality": quality,
        "outcome": "",
        "exit_price": "",
        "pnl_pips": "",
        "pnl_pct": "",
        "duration_hrs": "",
        "notes": notes,
    }

    rows.append(row)
    _write_all(rows)
    print(f"\n✅ Trade #{trade_id} logged → {LOG_PATH}")


def update_result():
    rows = _read_all()
    if not rows:
        print("No trades logged yet.")
        return

    print("\n── Open Trades ──────────────────────────────────────")
    open_trades = [r for r in rows if not r["outcome"]]
    if not open_trades:
        print("No open trades to update.")
        return

    for r in open_trades:
        print(f"  #{r['id']}  {r['pair']}  {r['direction']}  entry={r['entry']}  ({r['timestamp']})")

    trade_id = _prompt("\nTrade ID to update").strip()
    row = next((r for r in rows if r["id"] == trade_id), None)
    if row is None:
        print(f"Trade #{trade_id} not found.")
        return

    print(f"\n── Updating Trade #{trade_id} — {row['pair']} {row['direction']} ──")
    outcome    = _prompt("Outcome (TP/SL/TIMEOUT/MANUAL)").upper()
    exit_price = _prompt("Exit price")
    duration   = _prompt("Duration (hours, optional)")
    notes      = _prompt("Notes (optional)", default=row["notes"])

    pnl_pips, pnl_pct = _calc_pnl(row["direction"], row["entry"], exit_price)

    row.update({
        "outcome": outcome,
        "exit_price": exit_price,
        "pnl_pips": pnl_pips,
        "pnl_pct": pnl_pct,
        "duration_hrs": duration,
        "notes": notes,
    })

    _write_all(rows)
    print(f"\n✅ Trade #{trade_id} updated — {outcome}  {pnl_pips:+.1f} pips  ({pnl_pct:+.4f}%)")


def view_log():
    rows = _read_all()
    if not rows:
        print("No trades logged yet.")
        return

    print(f"\n{'#':<4} {'Pair':<12} {'Dir':<5} {'Conf':<6} {'Entry':<12} {'SL':<12} {'TP':<12} {'Outcome':<9} {'Pips':>7} {'%':>8}")
    print("─" * 90)
    for r in rows:
        pips = f"{float(r['pnl_pips']):+.1f}" if r["pnl_pips"] else "open"
        pct  = f"{float(r['pnl_pct']):+.4f}" if r["pnl_pct"] else "—"
        outcome = r["outcome"] or "open"
        print(f"{r['id']:<4} {r['pair']:<12} {r['direction']:<5} {r['confidence']:<6} "
              f"{r['entry']:<12} {r['sl']:<12} {r['tp']:<12} {outcome:<9} {pips:>7} {pct:>8}")

    # Summary
    closed = [r for r in rows if r["outcome"]]
    if closed:
        wins = [r for r in closed if r["outcome"] == "TP"]
        total_pips = sum(float(r["pnl_pips"]) for r in closed if r["pnl_pips"])
        print("─" * 90)
        print(f"Trades: {len(closed)} closed  |  Win rate: {len(wins)/len(closed)*100:.0f}%  |  Total: {total_pips:+.1f} pips")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "view"

    if cmd == "log":
        log_trade()
    elif cmd == "results":
        update_result()
    elif cmd == "view":
        view_log()
    else:
        print("Usage: python trade_log.py [log | results | view]")
        