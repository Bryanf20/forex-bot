import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import List
from backtesting.engine import Trade


def plot_backtest(
    df: pd.DataFrame,
    trades: List[Trade],
    equity_curve: pd.DataFrame,
    pair: str,
    timeframe: str,
    metrics: dict,
):
    """
    Save a 3-panel backtest chart:
      Panel 1 — Price + EMA lines + trade entry markers
      Panel 2 — RSI
      Panel 3 — Equity curve
    """
    os.makedirs("charts", exist_ok=True)
    safe_pair = pair.replace("=", "").replace("/", "_")

    fig = plt.figure(figsize=(16, 10))
    gs  = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1.5], hspace=0.35)

    ax_price  = fig.add_subplot(gs[0])
    ax_rsi    = fig.add_subplot(gs[1], sharex=ax_price)
    ax_equity = fig.add_subplot(gs[2])

    # ── Panel 1: Price + EMAs + trade markers ─────────────────────────
    ax_price.plot(df.index, df["close"],  label="Close",  linewidth=1.0, color="#4a90d9")
    ax_price.plot(df.index, df["ema_20"], label="EMA 20", linewidth=1.0, linestyle="--", color="#f5a623")
    ax_price.plot(df.index, df["ema_50"], label="EMA 50", linewidth=1.0, linestyle="--", color="#e74c3c")

    for t in trades:
        if t.entry_time in df.index:
            ep = t.entry_price
            color = "#27ae60" if t.direction == "BUY" else "#e74c3c"
            marker = "^" if t.direction == "BUY" else "v"
            ax_price.scatter(t.entry_time, ep, marker=marker, color=color, s=80, zorder=5)

        if t.exit_time in df.index and t.exit_reason in ("tp", "sl"):
            color = "#27ae60" if t.pnl_abs > 0 else "#e74c3c"
            ax_price.scatter(t.exit_time, t.exit_price, marker="x", color=color, s=60, zorder=5)

    ax_price.set_title(
        f"{pair} | {timeframe}  —  Backtest  "
        f"| WR {metrics['win_rate']*100:.1f}%  "
        f"| Return {metrics['total_return_pct']:+.1f}%  "
        f"| Sharpe {metrics['sharpe_ratio']:.2f}",
        fontsize=10,
    )
    ax_price.legend(fontsize=8)
    ax_price.grid(True, alpha=0.3)
    ax_price.set_ylabel("Price")

    # ── Panel 2: RSI ──────────────────────────────────────────────────
    if "rsi" in df.columns:
        ax_rsi.plot(df.index, df["rsi"], color="#9b59b6", linewidth=0.9)
        ax_rsi.axhline(70, color="#e74c3c", linestyle="--", linewidth=0.7, alpha=0.7)
        ax_rsi.axhline(30, color="#27ae60", linestyle="--", linewidth=0.7, alpha=0.7)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel("RSI", fontsize=8)
        ax_rsi.grid(True, alpha=0.3)

    # ── Panel 3: Equity curve ─────────────────────────────────────────
    ax_equity.plot(
        equity_curve.index,
        equity_curve["balance"],
        color="#2ecc71",
        linewidth=1.2,
        label="Equity",
    )
    ax_equity.axhline(
        equity_curve["balance"].iloc[0],
        color="gray",
        linestyle="--",
        linewidth=0.7,
        alpha=0.6,
        label="Start",
    )
    ax_equity.fill_between(
        equity_curve.index,
        equity_curve["balance"],
        equity_curve["balance"].iloc[0],
        alpha=0.15,
        color="#2ecc71",
    )
    ax_equity.set_ylabel("Balance ($)", fontsize=8)
    ax_equity.legend(fontsize=8)
    ax_equity.grid(True, alpha=0.3)

    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M")
    filename  = f"charts/{safe_pair}_{timeframe}_backtest_{timestamp}.png"
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved → {filename}")
    return filename