# mt5_utils.py
import MetaTrader5 as mt5
import pandas as pd
import logging
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_TERMINAL_PATH, SYMBOL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_mt5():
    """Initialize MetaTrader5 connection."""
    if not mt5.initialize(
        path=MT5_TERMINAL_PATH,
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER
    ):
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        mt5.shutdown()
        raise Exception("MT5 initialization failed")
    if not mt5.symbol_select(SYMBOL, True):
        logger.error(f"Symbol {SYMBOL} not available: {mt5.last_error()}")
        mt5.shutdown()
        raise Exception(f"Symbol {SYMBOL} not available")

def timeframe_to_minutes(timeframe):
    """Convert MT5 timeframe to minutes for validation."""
    timeframe_minutes = {
        mt5.TIMEFRAME_M1: 1,
        mt5.TIMEFRAME_M5: 5,
        mt5.TIMEFRAME_M15: 15,
        mt5.TIMEFRAME_M30: 30,
        mt5.TIMEFRAME_H1: 60,
        mt5.TIMEFRAME_H4: 240,
        mt5.TIMEFRAME_D1: 1440
    }
    return timeframe_minutes.get(timeframe, 1)

def fetch_ohlcv(symbol, timeframe, limit):
    """Fetch OHLCV data from MetaTrader5."""
    try:
        if not mt5.terminal_info():
            initialize_mt5()
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
        if rates is None or len(rates) == 0:
            logger.error(f"No data fetched from MT5 for {timeframe}: {mt5.last_error()}")
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df = df.rename(columns={
            'time': 'timestamp', 'open': 'open', 'high': 'high',
            'low': 'low', 'close': 'close', 'tick_volume': 'volume'
        })
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        if df[['open', 'high', 'low', 'close']].isnull().any().any():
            logger.warning(f"NaN values detected in OHLC data for {timeframe}")
            df = df.dropna()
        if df.empty:
            logger.error(f"DataFrame is empty after cleaning for {timeframe}")
            return None
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        df['volume'] = df['volume'].astype(int)
        df.set_index('timestamp', inplace=True)
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error(f"Index is not a DatetimeIndex after setting for {timeframe}")
            return None
        if df.index.duplicated().any():
            logger.warning(f"Duplicate timestamps detected for {timeframe}, removing duplicates")
            df = df[~df.index.duplicated(keep='last')]
        df = df.sort_index()
        time_diffs = df.index.to_series().diff().dropna()
        timeframe_minutes = timeframe_to_minutes(timeframe)
        if not time_diffs.empty and (time_diffs > pd.Timedelta(minutes=timeframe_minutes)).any():
            logger.warning(f"Non-sequential timestamps detected for timeframe {timeframe_minutes} minutes")
        logger.info(f"Fetched {len(df)} candles for {timeframe} from {df.index[0]} to {df.index[-1]}")
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV data for {timeframe}: {e}")
        return None