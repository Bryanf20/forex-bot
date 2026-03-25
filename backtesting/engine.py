import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Trade:
    entry_index: int
    entry_time: pd.Timestamp
    entry_price: float
    direction: str           # "BUY" or "SELL"
    confidence: float
    exit_index: Optional[int] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # "tp", "sl", "end"
    pnl_pct: Optional[float] = None
    pnl_abs: Optional[float] = None


class BacktestEngine:
    """
    Walk-forward backtester.

    Iterates over historical bars, calls strategy.apply() on each
    growing sub-DataFrame, and simulates trade entries / exits.

    Parameters
    ----------
    take_profit_pct : float   e.g. 0.02  → 2% TP
    stop_loss_pct   : float   e.g. 0.01  → 1% SL
    initial_balance : float   Starting account equity
    min_confidence  : float   Skip signals below this threshold
    warmup          : int     Bars to skip (indicator warmup period)
    """

    def __init__(
        self,
        take_profit_pct: float = 0.02,
        stop_loss_pct: float = 0.01,
        initial_balance: float = 1_000.0,
        min_confidence: float = 0.45,
        warmup: int = 100,
        max_bars: int = 48,
    ):
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.initial_balance = initial_balance
        self.min_confidence = min_confidence
        self.warmup = warmup
        self.max_bars = max_bars 

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, df: pd.DataFrame, strategy) -> dict:
        """
        Run the backtest.

        Parameters
        ----------
        df       : DataFrame with OHLCV + indicator columns pre-applied.
        strategy : Any object with apply(df) → (decision, reasons, confidence)

        Returns
        -------
        dict with keys: trades (List[Trade]), equity_curve (DataFrame)
        """
        trades: List[Trade] = []
        equity_curve: List[dict] = []

        balance = self.initial_balance
        open_trade: Optional[Trade] = None

        for i in range(self.warmup, len(df)):
            bar = df.iloc[i]
            current_price = float(bar["close"])
            current_time = df.index[i]

            # 1. Check if open trade hits TP / SL
            if open_trade is not None:
                closed, reason = self._check_exit(open_trade, bar, i)
                if closed:
                    pnl_pct, pnl_abs = self._calculate_pnl(open_trade, current_price)
                    open_trade.exit_index = i
                    open_trade.exit_time = current_time
                    open_trade.exit_price = current_price
                    open_trade.exit_reason = reason
                    open_trade.pnl_pct = pnl_pct
                    open_trade.pnl_abs = pnl_abs
                    balance += pnl_abs
                    trades.append(open_trade)
                    open_trade = None

            # 2. Generate signal on all data up to current bar
            sub_df = df.iloc[: i + 1]
            try:
                decision, reasons, confidence = strategy.apply(sub_df)
            except Exception:
                continue

            # 3. Open new trade if flat and signal is strong enough
            if open_trade is None and decision in ("BUY", "SELL"):
                if confidence >= self.min_confidence:
                    open_trade = Trade(
                        entry_index=i,
                        entry_time=current_time,
                        entry_price=current_price,
                        direction=decision,
                        confidence=confidence,
                    )

            # 4. Track running equity (includes unrealised P&L)
            unrealised = 0.0
            if open_trade is not None:
                _, unrealised = self._calculate_pnl(open_trade, current_price)

            equity_curve.append({
                "time": current_time,
                "balance": balance + unrealised,
            })

        # 5. Force-close any trade still open at end of data
        if open_trade is not None:
            last_price = float(df["close"].iloc[-1])
            pnl_pct, pnl_abs = self._calculate_pnl(open_trade, last_price)
            open_trade.exit_index = len(df) - 1
            open_trade.exit_time = df.index[-1]
            open_trade.exit_price = last_price
            open_trade.exit_reason = "end"
            open_trade.pnl_pct = pnl_pct
            open_trade.pnl_abs = pnl_abs
            trades.append(open_trade)

        equity_df = pd.DataFrame(equity_curve).set_index("time")

        return {
            "trades": trades,
            "equity_curve": equity_df,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_exit(self, trade: Trade, bar, current_bar_index: int) -> tuple:
        """Return (should_exit: bool, reason: str)."""

        # Max hold period exceeded
        if current_bar_index - trade.entry_index >= self.max_bars:
            return True, "timeout"
        
        price = float(bar["close"])

        if trade.direction == "BUY":
            if price >= trade.entry_price * (1 + self.take_profit_pct):
                return True, "tp"
            if price <= trade.entry_price * (1 - self.stop_loss_pct):
                return True, "sl"
        else:  # SELL
            if price <= trade.entry_price * (1 - self.take_profit_pct):
                return True, "tp"
            if price >= trade.entry_price * (1 + self.stop_loss_pct):
                return True, "sl"

        return False, ""

    def _calculate_pnl(self, trade: Trade, exit_price: float) -> tuple:
        if trade.direction == "BUY":
            pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        else:
            pnl_pct = (trade.entry_price - exit_price) / trade.entry_price

        pnl_abs = pnl_pct * self.initial_balance
        return round(pnl_pct, 6), round(pnl_abs, 4)
    