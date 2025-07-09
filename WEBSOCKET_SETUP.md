# WebSocket Data Collection Setup

This document explains how to set up and use the WebSocket data collection system for real-time stock and futures data from Fyers API.

## Overview

The WebSocket system collects real-time market data for all tickers in your database and stores them in dedicated websocket data tables. It supports both regular stock data and futures data.

## Components

### 1. Database Tables
For each ticker, the system automatically creates websocket data tables:
- `<ticker_symbol>_websocket_data` - Regular stock websocket data
- `<ticker_symbol>_future_websocket_data` - Futures websocket data

Each table contains:
- `timestamp` - When the data was received
- `ltp` - Last Traded Price

### 2. Celery Task
The `process_stock_data` task in `dashboard/tasks.py` processes incoming websocket messages and saves data to the appropriate tables.

### 3. Management Command
The `start_websocket` command in `dashboard/management/commands/start_websocket.py` starts the WebSocket connection.

### 4. Web Interface
View real-time websocket data through the web interface at `/websocket-data/<ticker_symbol>/`

## Setup Instructions

### 1. Prerequisites
Ensure you have:
- Redis running (for Celery)
- Celery worker running
- Fyers API access token configured in Django admin

### 2. Start Celery Worker
```bash
celery -A gurubase worker --loglevel=info
```

### 3. Start WebSocket Data Collection

#### For 50 stocks or less (Single Connection):
```bash
python manage.py start_websocket --limit 50
```

#### For 200-250 stocks (Multiple Connections):
```bash
python manage.py start_websocket_multi --max-stocks 250
```

#### Single WebSocket Options:
- `--limit 50` - Limit number of symbols to subscribe to (default: 50)
- `--litemode` - Enable lite mode for WebSocket connection

#### Multi-WebSocket Options:
- `--stocks-per-connection 50` - Number of stocks per connection (default: 50)
- `--max-stocks 250` - Maximum number of stocks to process (default: 250)
- `--litemode` - Enable lite mode for all WebSocket connections
- `--connection-delay 2` - Delay in seconds between starting connections (default: 2)

Examples:
```bash
# Single connection for 50 stocks
python manage.py start_websocket --limit 50 --litemode

# Multiple connections for 250 stocks
python manage.py start_websocket_multi --max-stocks 250 --litemode

# Custom configuration for 200 stocks with 40 stocks per connection
python manage.py start_websocket_multi --max-stocks 200 --stocks-per-connection 40
```

### 4. Monitor Progress
The management command will display:
- Connection status
- Number of symbols found and subscribed
- Real-time messages received
- Any errors encountered

## Usage

### Viewing WebSocket Data
1. Go to `/tickers/` in your web interface
2. Click **"WebSocket Monitor"** to see overall statistics for all tickers
3. Click **"WebSocket Data"** for any specific ticker to view real-time data with auto-refresh option

### Monitoring Multiple Connections
The **WebSocket Monitor** (`/websocket-monitor/`) provides:
- Real-time statistics for all tickers
- Connection status overview
- Data collection metrics
- Latest prices for futures and regular data
- Auto-refresh functionality

#### Multi-Connection Status Monitoring
When running `start_websocket_multi`, the command displays:
- Connection status for each WebSocket (🟢 CONNECTED / 🔴 DISCONNECTED)
- Number of messages processed per connection
- Total symbols being tracked
- Automatic status updates every 30 seconds

### Symbol Format
The system uses the format `NSE:SYMBOL25JULFUT` for futures data as per your preference.

Special symbol mappings:
- `BAJAJAUTO` → `NSE:BAJAJ-AUTO25JULFUT`
- `MM` → `NSE:M&M25JULFUT`
- `MMFIN` → `NSE:M&MFIN25JULFUT`

### Data Processing Flow
1. WebSocket receives real-time data from Fyers API
2. `onmessage` callback triggers `process_stock_data.delay(message)`
3. Celery task processes the message asynchronously
4. Data is parsed and saved to appropriate database tables
5. Web interface displays the saved data

## Troubleshooting

### Common Issues

1. **No Access Token Found**
   - Add access token in Django admin: `/admin/dashboard/accesstoken/`

2. **Celery Worker Not Running**
   ```bash
   celery -A gurubase worker --loglevel=info
   ```

3. **Redis Connection Issues**
   - Ensure Redis is running on localhost:6379
   - Check Redis configuration in settings.py

4. **WebSocket Connection Errors**
   - Verify access token is valid
   - Check network connectivity
   - Review Fyers API rate limits

5. **No Data in Tables**
   - Check if tickers exist in TickerBase model
   - Verify symbol formatting matches Fyers API requirements
   - Check Celery logs for processing errors

### Logs
Monitor logs for:
- Django logs: Check console output from management command
- Celery logs: Monitor task processing
- Database logs: Verify data insertion

### Performance Considerations
- Default limit is 50 symbols to avoid overwhelming the API
- Each symbol generates frequent updates during market hours
- Consider database maintenance for websocket tables (they grow quickly)
- Use litemode for better performance if detailed data isn't needed

## API Integration

### Fyers WebSocket Configuration
```python
fyers = data_ws.FyersDataSocket(
    access_token=access_token,
    log_path="",
    litemode=False,  # Set to True for lite mode
    write_to_file=False,
    reconnect=True,  # Auto-reconnect on connection loss
    on_connect=onopen,
    on_close=onclose,
    on_error=onerror,
    on_message=onmessage
)
```

### Data Types
Subscribe to `SymbolUpdate` data type for real-time price updates.

## Maintenance

### Cleaning Old Data
WebSocket tables can grow large. Consider implementing data retention policies:

```sql
-- Example: Delete data older than 7 days
DELETE FROM "ticker_websocket_data" 
WHERE timestamp < NOW() - INTERVAL '7 days';
```

### Monitoring
- Monitor Celery queue length
- Check database table sizes
- Monitor API usage and rate limits
- Track WebSocket connection stability

## Integration with Existing System

This WebSocket system integrates seamlessly with your existing:
- Historical data collection (`update_historical_data` task)
- SSE streams for real-time dashboard updates
- Technical indicator calculations
- Alert system for strategy notifications

The real-time websocket data can be used to enhance your existing features with live market data. 