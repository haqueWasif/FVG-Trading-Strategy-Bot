import asyncio
from datetime import datetime
import logging
import matplotlib.pyplot as plt
from mt5_utils import initialize_mt5, fetch_ohlcv
from telegram_utils import send_telegram_message
from fvg_analysis import detect_fvg, generate_signal
from plotting import plot_fvg_multi
from config import SYMBOL, LIMIT, PLOT_TIMEFRAMES, TIMEFRAME_MAP
from IPython.display import display

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main loop to run the FVG trading bot."""
    logger.info(f"Starting real-time FVG signal bot for {SYMBOL} with multi-timeframe plotting...")
    try:
        initialize_mt5()
    except Exception as e:
        logger.error(f"Failed to initialize MT5: {e}")
        raise
    
    last_signal_times = {tf: None for tf in PLOT_TIMEFRAMES}  # Track last signal time per timeframe
    first_run = True
    while True:
        try:
            # Fetch data for all timeframes
            data_dict = {}
            for tf in PLOT_TIMEFRAMES:
                df = fetch_ohlcv(SYMBOL, TIMEFRAME_MAP[tf], LIMIT)
                if df is not None:
                    df, fvg_zones = detect_fvg(df, tf)
                else:
                    fvg_zones = []
                data_dict[tf] = {'df': df, 'fvg_zones': fvg_zones}
            
            # Generate signals for all timeframes
            for tf in PLOT_TIMEFRAMES:
                tf_df = data_dict[tf]['df']
                tf_fvg_zones = data_dict[tf]['fvg_zones']
                if tf_df is not None:
                    signal = generate_signal(tf_df, tf_fvg_zones, TIMEFRAME_MAP[tf])
                    if signal:
                        logger.info(f"Signal generated for {tf}: {signal['type']} at {signal['price']}")
                        current_time = signal['timestamp']
                        if last_signal_times[tf] is None or (current_time - last_signal_times[tf]).total_seconds() > 60:
                            message = (
                                f"🚨 {signal['type']} Signal for {SYMBOL} ({tf})\n"
                                f"📅 Time: {signal['timestamp']}\n"
                                f"💰 Entry Price: {signal['price']:.5f}\n"
                                f"🔍 FVG Zone: {signal['fvg_low']:.5f} - {signal['fvg_high']:.5f}\n"
                                f"🛑 Stop Loss: {signal['stop_loss']:.5f}\n"
                                f"🎯 Take Profit: {signal['take_profit']:.5f}"
                            )
                            await send_telegram_message(message)
                            last_signal_times[tf] = current_time
                    else:
                        logger.info(f"No signal generated for {tf}")
            
            # Plot with slider
            plot_fvg_multi(data_dict, initial=first_run)
            if first_run:
                plt.gcf()
                plt.show()
                first_run = False
            
            current_second = datetime.utcnow().second
            sleep_time = max(60 - current_second + 1, 1)
            await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()