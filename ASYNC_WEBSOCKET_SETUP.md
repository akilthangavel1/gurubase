# Async WebSocket Processing System

This document explains the new async WebSocket processing system that separates WebSocket connections from data processing using Celery for improved stability and performance.

## System Architecture

### Components

1. **AsyncWebSocketManager** - Manages multiple WebSocket connections
2. **Celery Tasks** - Processes incoming WebSocket data asynchronously
3. **Dedicated Queue** - `websocket_data` queue for efficient task distribution
4. **Automatic Reconnection** - Handles connection failures gracefully
5. **Comprehensive Monitoring** - Real-time stats and health checking

### Benefits

- ✅ **Non-blocking processing** - WebSocket connections don't wait for data processing
- ✅ **Better stability** - Connection failures don't affect data processing
- ✅ **Scalable** - Can handle high-frequency data with multiple workers
- ✅ **Fault tolerant** - Automatic retries and reconnection
- ✅ **Load balanced** - Tasks distributed across multiple Celery workers

## Quick Start

### Option 1: Use the Startup Script (Recommended)

```bash
# Start both Celery worker and WebSocket connections
python start_websocket_system.py

# With custom configuration
python start_websocket_system.py --stocks-per-connection=40 --max-stocks=200 --litemode

# See all options
python start_websocket_system.py --help
```

### Option 2: Manual Setup

1. **Start Celery Worker** (in one terminal):
```bash
python manage.py celery_worker --concurrency=4 --loglevel=info
```

2. **Start WebSocket Connections** (in another terminal):
```bash
python manage.py start_websocket_multi --stocks-per-connection=50 --max-stocks=250
```

## Configuration Options

### WebSocket Manager Options

| Option | Default | Description |
|--------|---------|-------------|
| `--stocks-per-connection` | 50 | Number of stocks per WebSocket connection |
| `--max-stocks` | 250 | Maximum number of stocks to process |
| `--connection-delay` | 3 | Delay between starting connections (seconds) |
| `--monitor-interval` | 30 | Monitoring update interval (seconds) |
| `--litemode` | False | Enable lite mode for connections |

### Celery Worker Options

| Option | Default | Description |
|--------|---------|-------------|
| `--concurrency` | 4 | Number of worker processes |
| `--loglevel` | info | Logging level (debug, info, warning, error) |
| `--queue` | websocket_data | Queue name to listen to |

## System Flow

```
WebSocket Data → Queue → Celery Worker → Database
       ↓              ↓           ↓           ↓
   Non-blocking   Distributed  Async     Efficient
   Processing     Load        Processing  Storage
```

### Detailed Flow

1. **WebSocket receives data** - Each connection processes messages independently
2. **Queue task** - Data is queued to `websocket_data` queue using `apply_async()`
3. **Celery worker picks up task** - Workers process tasks from the queue
4. **Process data** - Extract symbol, validate, and save to database
5. **Handle failures** - Automatic retries with exponential backoff
6. **Return results** - Task returns status for monitoring

## Monitoring

### Real-time Status Display

The system provides comprehensive monitoring:

```
📊 ASYNC CONNECTION STATUS [15:47:50]:
   🟢 Connected: 4/5 connections
   📨 Total messages: 145,955
   ❌ Total errors: 12
   🔄 Processing: Async via Celery

   Connection 1: 🔴 (2,345 msgs, 1 errs, 50 symbols, last: 15:47:49)
   Connection 2: 🟢 (45,123 msgs, 0 errs, 50 symbols, last: 15:47:50)
   Connection 3: 🟢 (52,876 msgs, 2 errs, 50 symbols, last: 15:47:50)
   Connection 4: 🟢 (43,210 msgs, 1 err, 50 symbols, last: 15:47:50)
   Connection 5: 🟢 (2,401 msgs, 8 errs, 21 symbols, last: 15:47:50)
      🔄 Reconnect attempts: 2
```

### Key Metrics

- **Connection Status** - Real-time connection health
- **Message Counts** - Messages processed per connection
- **Error Tracking** - Error counts with automatic retry info
- **Last Message Time** - When each connection last received data
- **Reconnection Attempts** - Automatic recovery status

## Error Handling & Recovery

### Connection-Level Recovery

- **Automatic Reconnection** - Failed connections automatically retry
- **Exponential Backoff** - Delays increase with each retry attempt
- **Max Retry Limits** - Prevents infinite retry loops
- **Graceful Degradation** - Other connections continue working

### Task-Level Recovery

- **Retry Policies** - Failed tasks retry with configurable policies
- **Fallback Methods** - Legacy table insertion if main method fails
- **Error Logging** - Comprehensive error tracking and reporting
- **Status Returns** - Tasks return detailed status information

## Performance Optimization

### Recommended Settings

For **high-frequency trading** environments:
```bash
python start_websocket_system.py \
    --stocks-per-connection=30 \
    --max-stocks=300 \
    --connection-delay=2 \
    --monitor-interval=15
```

For **development/testing**:
```bash
python start_websocket_system.py \
    --stocks-per-connection=20 \
    --max-stocks=100 \
    --litemode \
    --monitor-interval=60
```

### Scaling Guidelines

| Stock Count | Connections | Worker Processes | Memory Usage |
|-------------|-------------|------------------|--------------|
| 0-100       | 2           | 2-4              | ~500MB       |
| 100-250     | 3-5         | 4-6              | ~1GB         |
| 250-500     | 5-10        | 6-12             | ~2GB         |
| 500+        | 10+         | 12+              | ~4GB+        |

## Database Integration

### Primary Method: TickerPriceData Model
- Updates existing records or creates new ones
- Uses Django ORM for data integrity
- Automatic timestamp management

### Fallback Method: Legacy Tables
- Direct SQL insertion for compatibility
- Used when primary method fails
- Maintains data continuity

### Symbol Processing

The system handles symbol formatting automatically:
- **Input**: `NSE:RELIANCE25JULFUT`
- **Processed**: `reliance` (lowercase, cleaned)
- **Database**: Matches against `TickerBase.ticker_symbol`

## Troubleshooting

### Common Issues

**"No access token found"**
```bash
# Add access token via Django admin or shell
python manage.py shell
>>> from dashboard.models import AccessToken
>>> AccessToken.objects.create(value="your_token_here")
```

**Celery worker not starting**
```bash
# Check if Celery is installed
pip install celery

# Check for Redis/RabbitMQ broker
# Update CELERY_BROKER_URL in settings.py
```

**Connections dropping frequently**
- Check network stability
- Verify API rate limits
- Monitor system resources
- Consider reducing `stocks_per_connection`

**High memory usage**
- Reduce `concurrency` setting
- Lower `max_stocks` parameter
- Enable `--litemode`
- Monitor task queue size

### Debug Mode

Enable detailed logging:
```bash
# Celery worker with debug logging
python manage.py celery_worker --loglevel=debug

# WebSocket connections with debug output
python manage.py start_websocket_multi --monitor-interval=5
```

## Advanced Configuration

### Custom Celery Configuration

In `gurubase/settings.py`:
```python
# Celery Configuration for WebSocket Processing
CELERY_TASK_ROUTES = {
    'dashboard.tasks.process_stock_data': {'queue': 'websocket_data'},
}

CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # For high-frequency data
CELERY_TASK_ACKS_LATE = True          # Ensure task completion
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Prevent memory leaks
```

### Message Broker Optimization

For **Redis**:
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

For **RabbitMQ**:
```python
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
```

## Migration from Old System

### Key Changes

1. **Synchronous → Asynchronous**: Data processing no longer blocks connections
2. **Single-threaded → Multi-worker**: Parallel processing capabilities  
3. **No retries → Automatic retries**: Built-in fault tolerance
4. **Manual monitoring → Real-time stats**: Comprehensive system visibility

### Backward Compatibility

- Existing `TickerPriceData` model unchanged
- Legacy table fallback maintained
- Same symbol formatting and database structure
- Compatible with existing views and APIs

## Support

For issues or questions:
1. Check the monitoring output for connection status
2. Review Celery worker logs for task errors
3. Verify database connectivity and permissions
4. Monitor system resources (CPU, memory, network)

The async WebSocket processing system provides a robust, scalable solution for high-frequency financial data processing with built-in fault tolerance and comprehensive monitoring. 