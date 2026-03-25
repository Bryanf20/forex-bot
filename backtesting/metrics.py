import math
import pandas as pd
from typing import List
from backtesting.engine import Trade


def compute_metrics(trades: List[Trade], equity_curve: pd.DataFrame, initial_balance: float = 1_000.0) -> dict:
    """
    Compute a full suite of backtest performance metrics.

    Returns a dict with:
        total_trades, win_rate, avg_win_pct, avg_loss_pct,
        profit_factor, total_return_pct, max_drawdown_pct,
        sharpe_ratio, win_rate_by_direction, exit_reason_breakdown
    """
    if not trades:
        return {"error": "No trades to analyse"}

    # ── Basic counts ──────────────────────────────────────────────────
    total = len(trades)
    winners = [t for t in trades if t.pnl_pct > 0]
    losers  = [t for t in trades if t.pnl_pct <= 0]
    wins    = len(winners)
    losses  = len(losers)
    win_rate = wins / total if total else 0.0

    # ── Average P&L ───────────────────────────────────────────────────
    avg_win_pct  = sum(t.pnl_pct for t in winners) / wins   if wins   else 0.0
    avg_loss_pct = sum(t.pnl_pct for t in losers)  / losses if losses else 0.0

    # ── Profit factor  (gross profit / gross loss) ────────────────────
    gross_profit = sum(t.pnl_abs for t in winners)
    gross_loss   = abs(sum(t.pnl_abs for t in losers))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    # ── Total return ──────────────────────────────────────────────────
    final_balance  = initial_balance + sum(t.pnl_abs for t in trades)
    total_return_pct = (final_balance - initial_balance) / initial_balance * 100

    # ── Max drawdown ──────────────────────────────────────────────────
    max_drawdown_pct = _max_drawdown(equity_curve["balance"])

    # ── Sharpe ratio (annualised, assuming hourly bars) ───────────────
    sharpe = _sharpe_ratio(equity_curve["balance"])

    # ── Win rate by direction ─────────────────────────────────────────
    buy_trades  = [t for t in trades if t.direction == "BUY"]
    sell_trades = [t for t in trades if t.direction == "SELL"]

    win_rate_by_direction = {
        "BUY":  _win_rate(buy_trades),
        "SELL": _win_rate(sell_trades),
    }

    # ── Exit reason breakdown ─────────────────────────────────────────
    exit_reasons = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    # ── Confidence vs win correlation ─────────────────────────────────
    conf_vs_win = _confidence_buckets(trades)

    return {
        "total_trades":          total,
        "wins":                  wins,
        "losses":                losses,
        "win_rate":              round(win_rate, 4),
        "avg_win_pct":           round(avg_win_pct * 100, 3),
        "avg_loss_pct":          round(avg_loss_pct * 100, 3),
        "profit_factor":         round(profit_factor, 3),
        "gross_profit":          round(gross_profit, 4),
        "gross_loss":            round(gross_loss, 4),
        "total_return_pct":      round(total_return_pct, 3),
        "final_balance":         round(final_balance, 4),
        "max_drawdown_pct":      round(max_drawdown_pct, 3),
        "sharpe_ratio":          round(sharpe, 3),
        "win_rate_by_direction": win_rate_by_direction,
        "exit_reason_breakdown": exit_reasons,
        "confidence_buckets":    conf_vs_win,
    }


def trades_to_dataframe(trades: List[Trade]) -> pd.DataFrame:
    """Convert list of Trade objects to a readable DataFrame."""
    rows = []
    for t in trades:
        rows.append({
            "entry_time":   t.entry_time,
            "exit_time":    t.exit_time,
            "direction":    t.direction,
            "entry_price":  t.entry_price,
            "exit_price":   t.exit_price,
            "exit_reason":  t.exit_reason,
            "confidence":   t.confidence,
            "pnl_pct":      round(t.pnl_pct * 100, 3) if t.pnl_pct else None,
            "pnl_abs":      t.pnl_abs,
        })
    return pd.DataFrame(rows)


def print_summary(metrics: dict):
    """Pretty-print the metrics dict to stdout."""
    sep = "─" * 42
    print(f"\n{'═' * 42}")
    print("  BACKTEST RESULTS")
    print(f"{'═' * 42}")
    print(f"  Trades          : {metrics['total_trades']}  (W {metrics['wins']} / L {metrics['losses']})")
    print(f"  Win Rate        : {metrics['win_rate'] * 100:.1f}%")
    print(sep)
    print(f"  Avg Win         : +{metrics['avg_win_pct']:.2f}%")
    print(f"  Avg Loss        :  {metrics['avg_loss_pct']:.2f}%")
    print(f"  Profit Factor   : {metrics['profit_factor']:.2f}")
    print(sep)
    print(f"  Total Return    : {metrics['total_return_pct']:+.2f}%")
    print(f"  Final Balance   : ${metrics['final_balance']:,.2f}")
    print(f"  Max Drawdown    : {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio    : {metrics['sharpe_ratio']:.2f}")
    print(sep)
    print(f"  Win Rate BUY    : {metrics['win_rate_by_direction']['BUY'] * 100:.1f}%")
    print(f"  Win Rate SELL   : {metrics['win_rate_by_direction']['SELL'] * 100:.1f}%")
    print(sep)
    print("  Exit Reasons:")
    for reason, count in metrics["exit_reason_breakdown"].items():
        print(f"    {reason:<8}: {count}")
    print(sep)
    print("  Confidence Buckets (win rate per confidence band):")
    for bucket, stats in metrics["confidence_buckets"].items():
        wr = stats["win_rate"] * 100
        n  = stats["count"]
        print(f"    {bucket}: {wr:.0f}% win rate  (n={n})")
    print(f"{'═' * 42}\n")


# ── Private helpers ────────────────────────────────────────────────────

def _max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max * 100
    return abs(drawdown.min())


def _sharpe_ratio(equity: pd.Series, periods_per_year: int = 8_760) -> float:
    """Annualised Sharpe assuming hourly bars (8760 hrs/yr)."""
    returns = equity.pct_change().dropna()
    if returns.std() == 0:
        return 0.0
    return (returns.mean() / returns.std()) * math.sqrt(periods_per_year)


def _win_rate(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    return sum(1 for t in trades if t.pnl_pct > 0) / len(trades)


def _confidence_buckets(trades: List[Trade]) -> dict:
    """Group trades into confidence bands and compute win rate per band."""
    bands = {
        "0.0–0.4": [],
        "0.4–0.6": [],
        "0.6–0.8": [],
        "0.8–1.0": [],
    }
    for t in trades:
        c = t.confidence
        if c < 0.4:
            bands["0.0–0.4"].append(t)
        elif c < 0.6:
            bands["0.4–0.6"].append(t)
        elif c < 0.8:
            bands["0.6–0.8"].append(t)
        else:
            bands["0.8–1.0"].append(t)

    result = {}
    for band, ts in bands.items():
        result[band] = {
            "count":    len(ts),
            "win_rate": _win_rate(ts),
        }
    return result
