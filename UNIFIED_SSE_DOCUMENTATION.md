# Unified SSE Stream Documentation

## Overview

The unified SSE (Server-Sent Events) endpoint consolidates all three data streams (dynamic, static, and indicators) into a single endpoint that can yield different types of data separately based on their processing times and refresh intervals.

## Key Features

- **Multiple data types in one stream**: Dynamic data, static data, and technical indicators
- **Independent refresh rates**: Each data type has its own refresh interval
- **Processing time tracking**: Monitor how long each data type takes to process
- **Error handling**: Separate error reporting for each data type
- **Flexible parameters**: Customize timeframes and indicator settings

## Endpoint URL

```
/maindas/unified-stream/
```

## Query Parameters

### Required Parameters
- `data_types` (string): Comma-separated list of data types to stream
  - Valid values: `dynamic`, `static`, `indicators`
  - Example: `dynamic,static,indicators`

### Optional Parameters
- `timeframe` (string): Data timeframe (default: `1`)
  - Valid values: `1`, `5`, `15`, `30`, `60`, `240`, `1440`
- `ema` (string): EMA length for indicators (default: `10`)
- `sma` (string): SMA length for indicators (default: `10`)
- `hma` (string): HMA length for indicators (default: `10`)
- `macd` (string): MACD parameters in format "fast,slow,signal" (default: `12,26,9`)
- `supertrendLength` (string): Supertrend length (default: `14`)
- `supertrendMultiplier` (string): Supertrend multiplier (default: `3`)
- `keltnerEmaLength` (string): Keltner EMA length (default: `20`)
- `keltnerAtrLength` (string): Keltner ATR length (default: `14`)
- `keltnerMultiplier` (string): Keltner multiplier (default: `2`)

## Data Types and Refresh Intervals

| Data Type | Refresh Interval | Description |
|-----------|------------------|-------------|
| `dynamic` | 1 second | Real-time OHLCV data with ATP, swings, and bias |
| `static` | 5 seconds | Daily/weekly/monthly metrics and ranges |
| `indicators` | 2 seconds | Technical indicators (EMA, SMA, MACD, etc.) |

## Response Format

Each SSE message contains a JSON object with the following structure:

```json
{
  "type": "dynamic|static|indicators|error",
  "data": [...],
  "timestamp": 1234567890.123,
  "processing_time": 0.456
}
```

### Fields Explanation

- `type`: The type of data being sent
- `data`: Array of ticker data objects
- `timestamp`: Unix timestamp when the data was generated
- `processing_time`: Time taken to process this data type (in seconds)

## Example Usage

### JavaScript Client

```javascript
// Create EventSource with parameters
const params = new URLSearchParams({
    data_types: 'dynamic,indicators',
    timeframe: '5',
    ema: '20',
    sma: '50'
});

const eventSource = new EventSource(`/maindas/unified-stream/?${params.toString()}`);

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'dynamic':
            console.log('Dynamic data received:', data.data);
            console.log('Processing time:', data.processing_time, 'seconds');
            break;
            
        case 'indicators':
            console.log('Indicators data received:', data.data);
            break;
            
        case 'error':
            console.error('Error:', data.error);
            break;
    }
};
```

### Python Client

```python
import requests
import json

url = "http://your-domain/maindas/unified-stream/"
params = {
    'data_types': 'dynamic,static',
    'timeframe': '1'
}

response = requests.get(url, params=params, stream=True)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        data = json.loads(line[6:])  # Remove 'data: ' prefix
        print(f"Received {data['type']} data")
        print(f"Processing time: {data['processing_time']:.3f}s")
```

## Data Structure Examples

### Dynamic Data Response
```json
{
  "type": "dynamic",
  "data": [
    {
      "ticker_symbol": "NIFTY",
      "current_candle_open": 18500.25,
      "current_candle_high": 18520.50,
      "current_candle_low": 18495.75,
      "current_candle_close": 18510.00,
      "current_candle_atp": 18508.75,
      "bias": "BULLISH",
      "prev_swing_high_1": 18540.25,
      "prev_swing_low_1": 18470.50
    }
  ],
  "timestamp": 1234567890.123,
  "processing_time": 0.234
}
```

### Static Data Response
```json
{
  "type": "static",
  "data": [
    {
      "ticker_symbol": "NIFTY",
      "daily_high_latest": 18550.00,
      "daily_low_latest": 18400.25,
      "daily_close_latest": 18510.00,
      "highest_top_out_of_last_5_daily_tops_with_date": 18600.50,
      "lowest_bottom_out_of_last_5_daily_bottoms_with_date": 18300.75
    }
  ],
  "timestamp": 1234567890.123,
  "processing_time": 0.456
}
```

### Indicators Data Response
```json
{
  "type": "indicators",
  "data": [
    {
      "ticker_symbol": "NIFTY",
      "ema": 18505.25,
      "sma": 18500.75,
      "hma": 18508.50,
      "macd": 12.34,
      "signal_line": 10.56,
      "supertrend": 18450.25,
      "pivot": 18500.00,
      "r1": 18520.50,
      "s1": 18479.50
    }
  ],
  "timestamp": 1234567890.123,
  "processing_time": 0.678
}
```

## Error Handling

Errors are sent as separate SSE messages:

```json
{
  "type": "error",
  "error": "Error message description",
  "data_type": "dynamic",
  "timestamp": 1234567890.123
}
```

## Performance Considerations

1. **Selective Data Types**: Only request the data types you need to reduce server load
2. **Timeframe Selection**: Higher timeframes (60, 240, 1440) require less processing
3. **Connection Management**: Properly close EventSource connections when done
4. **Error Recovery**: Implement reconnection logic for network failures

## Testing

Access the example page to test the unified SSE:
```
http://your-domain/maindas/unified-example/
```

## Migration from Individual Endpoints

### Old Approach (Multiple Connections)
```javascript
// Three separate connections
const dynamicSource = new EventSource('/maindas/stream-dynamic-data/?timeframe=1');
const staticSource = new EventSource('/maindas/sse-static-data/?timeframe=1');
const indicatorSource = new EventSource('/maindas/stream_indicator_data/?timeframe=1');
```

### New Approach (Single Connection)
```javascript
// One connection for all data types
const unifiedSource = new EventSource('/maindas/unified-stream/?data_types=dynamic,static,indicators&timeframe=1');
```

## Benefits

1. **Reduced Connection Overhead**: Single WebSocket connection instead of multiple
2. **Better Resource Management**: Server can optimize data fetching across types
3. **Timing Flexibility**: Different refresh rates for different data types
4. **Centralized Error Handling**: All errors reported through one stream
5. **Performance Monitoring**: Built-in processing time tracking

## Backward Compatibility

The individual SSE endpoints remain available for backward compatibility:
- `/maindas/stream-dynamic-data/`
- `/maindas/sse-static-data/`
- `/maindas/stream_indicator_data/` 