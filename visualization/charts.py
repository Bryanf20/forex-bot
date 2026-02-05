import matplotlib.pyplot as plt
import os

def plot_with_signal(df, signal):
    plt.figure(figsize=(14, 7))

    plt.plot(df.index, df["close"], label="Close Price", linewidth=1.2)
    plt.plot(df.index, df["ema_20"], label="EMA 20", linestyle="--")
    plt.plot(df.index, df["ema_50"], label="EMA 50", linestyle="--")

    last_index = df.index[-1]
    last_close = df["close"].iloc[-1]

    if signal.signal == "BUY":
        plt.scatter(
            last_index,
            last_close,
            marker="^",
            s=120
        )
    elif signal.signal == "SELL":
        plt.scatter(
            last_index,
            last_close,
            marker="v",
            s=120
        )

    plt.title(f"{signal.pair} | {signal.timeframe} | Signal: {signal.signal}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_chart(df, pair, timeframe, signal):
    # Ensure charts directory exists
    os.makedirs("charts", exist_ok=True)

    # Sanitize pair name for filesystem safety
    safe_pair = pair.replace("=", "").replace("/", "_")

    plt.figure(figsize=(12, 6))

    plt.plot(df["close"], label="Price", linewidth=1)
    plt.plot(df["ema_20"], label="EMA 20")
    plt.plot(df["ema_50"], label="EMA 50")

    plt.title(f"{pair} {timeframe} | Signal: {signal.signal}")
    plt.legend()
    plt.grid(True)

    filename = (
        f"charts/{safe_pair}_{timeframe}_"
        f"{signal.timestamp:%Y%m%d_%H%M}.png"
    )

    plt.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Chart saved → {filename}")
