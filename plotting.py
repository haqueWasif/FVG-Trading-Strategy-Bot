# plotting.py
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import mplfinance as mpf
import logging
from config import DISPLAY_CANDLES, PLOT_TIMEFRAMES

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for plotting
fig = None
axes = None
slider = None
data_dict_global = None

def plot_fvg_multi(data_dict, initial=False):
    """Plot FVG zones for multiple timeframes with a slider."""
    global fig, axes, slider, data_dict_global
    data_dict_global = data_dict

    if initial or fig is None:
        # Clear any existing figures to avoid overlap
        plt.close('all')
        # Set up figure with increased size for clarity
        fig = plt.figure(figsize=(12, 8), dpi=150)
        gs = fig.add_gridspec(2, 2, top=0.92, bottom=0.18, hspace=0.4, wspace=0.3)
        axes = [fig.add_subplot(gs[i//2, i%2]) for i in range(4)]
        slider_ax = fig.add_axes([0.15, 0.05, 0.7, 0.04])
        
        max_candles = min([len(data_dict[tf]['df']) if data_dict[tf]['df'] is not None else 0 for tf in PLOT_TIMEFRAMES])
        if max_candles <= DISPLAY_CANDLES:
            logger.warning("Not enough data for sliding window")
            for ax, tf in zip(axes, PLOT_TIMEFRAMES):
                ax.text(0.5, 0.5, f"No data for {tf}", ha='center', va='center')
                ax.set_title(f"{tf} Chart")
            plt.tight_layout(pad=2.0)
            fig.canvas.draw()  # Draw even if no data
            return
        
        slider = Slider(slider_ax, 'Candle Index', 0, max_candles - DISPLAY_CANDLES, valinit=max_candles - DISPLAY_CANDLES, valstep=1)
        slider.on_changed(update)
        logger.debug("Slider initialized")
    
    update(slider.val if slider else 0)
    fig.canvas.draw()  # Ensure canvas is drawn after update
    fig.canvas.flush_events()  # Process GUI events
    plt.tight_layout(pad=2.0)
    logger.debug("Plot updated")
def update(val):
    """Update the plot based on slider position."""
    global axes, data_dict_global
    if data_dict_global is None:
        return
    
    start_idx = int(val)
    for ax, tf in zip(axes, PLOT_TIMEFRAMES):
        ax.clear()
        df = data_dict_global[tf]['df']
        fvg_zones = data_dict_global[tf]['fvg_zones']
        
        if df is None or df.empty:
            ax.text(0.5, 0.5, f"No data for {tf}", ha='center', va='center')
            ax.set_title(f"{tf} Chart")
            continue
        
        window_df = df.iloc[start_idx:start_idx + DISPLAY_CANDLES]
        if window_df.empty:
            ax.text(0.5, 0.5, f"No data in window for {tf}", ha='center', va='center')
            ax.set_title(f"{tf} Chart")
            continue
        
        try:
            # Plot with explicit tight_layout to avoid overlap
            mpf.plot(
                window_df[['open', 'high', 'low', 'close']],
                type='candle',
                volume=False,
                ax=ax,
                ylabel='Price',
                show_nontrading=False,
                tight_layout=False,  # Let matplotlib handle layout
             
            )
            logger.info(f"Candlestick chart plotted for {tf} at index {start_idx}")
        except Exception as e:
            logger.error(f"Error plotting candlestick chart for {tf}: {e}")
            ax.plot(window_df.index, window_df['open'], label='Open', color='blue', alpha=0.5)
            ax.plot(window_df.index, window_df['high'], label='High', color='green', alpha=0.5)
            ax.plot(window_df.index, window_df['low'], label='Low', color='red', alpha=0.5)
            ax.plot(window_df.index, window_df['close'], label='Close', color='black')
            ax.set_title(f"{tf} Fallback: Raw OHLC Prices")
            ax.legend()
            continue
        
        # Plot FVG zones within the window
        bullish_labeled = False
        bearish_labeled = False
        for start_time, end_time, fvg_low, fvg_high, fvg_type in fvg_zones:
            if start_time >= window_df.index[0] and end_time <= window_df.index[-1]:
                try:
                    start_idx_rel = window_df.index.get_loc(start_time)
                    end_idx_rel = window_df.index.get_loc(end_time)
                    color = 'green' if fvg_type == 'bullish' else 'red'
                    label = None
                    if fvg_type == 'bullish' and not bullish_labeled:
                        label = 'Bullish FVG'
                        bullish_labeled = True
                    elif fvg_type == 'bearish' and not bearish_labeled:
                        label = 'Bearish FVG'
                        bearish_labeled = True
                    ax.fill_betweenx(
                        y=[fvg_low, fvg_high],
                        x1=start_idx_rel,
                        x2=end_idx_rel,
                        color=color,
                        alpha=0.3,
                        linewidth=0,
                        label=label
                    )
                except KeyError:
                    logger.warning(f"Skipping FVG zone for {tf} due to missing timestamp")
                    continue
                except Exception as e:
                    logger.warning(f"Error plotting FVG zone for {tf}: {e}")
                    continue
        
        # Set y-axis limits to include FVG zones
        if not window_df.empty:
            y_min = min(window_df['low'].min(), min([z[2] for z in fvg_zones if z[0] >= window_df.index[0] and z[1] <= window_df.index[-1]] or [window_df['low'].min()])) * 0.999
            y_max = max(window_df['high'].max(), max([z[3] for z in fvg_zones if z[0] >= window_df.index[0] and z[1] <= window_df.index[-1]] or [window_df['high'].max()])) * 1.001
            ax.set_ylim(y_min, y_max)
            logger.info(f"Set y-axis limits for {tf}: {y_min} to {y_max}")
        
        if bullish_labeled or bearish_labeled:
            ax.legend()
        ax.set_title(f"{tf} Chart", pad=10)  # Add padding to title
    
    fig.canvas.draw_idle()
    logger.info(f"Updated plot with slider at index {start_idx}")