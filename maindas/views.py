from django.shortcuts import render
from django.http import StreamingHttpResponse
import asyncio
import json
import logging
from django.core.serializers.json import DjangoJSONEncoder
from .dynamicdata import retrieve_latest_data
from .staticdata import fetch_latest_data as fetch_static_data
from .indfuture import fetch_latest_data as fetch_indicator_data
from dashboard.models import TickerBase
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


def unified_sse_stream(request):
    """
    Unified SSE endpoint that can stream different types of data based on request parameters.
    
    Query parameters:
    - data_types: comma-separated list of data types ('dynamic', 'static', 'indicators')
    - timeframe: timeframe for the data (default: '1')
    - For indicators: ema, sma, hma, macd, supertrendLength, supertrendMultiplier, etc.
    """
    # Parse request parameters
    data_types_param = request.GET.get('data_types', 'dynamic')
    data_types = [dt.strip() for dt in data_types_param.split(',')]
    
    # Common parameters
    timeframe = request.GET.get('timeframe', '1')
    
    # Indicator-specific parameters
    indicator_params = {
        'ema': request.GET.get('ema', '10'),
        'sma': request.GET.get('sma', '10'),
        'hma': request.GET.get('hma', '10'),
        'macd': request.GET.get('macd', '12,26,9'),
        'supertrend_length': request.GET.get('supertrendLength', '14'),
        'supertrend_multiplier': request.GET.get('supertrendMultiplier', '3'),
        'keltner_ema_length': request.GET.get('keltnerEmaLength', '20'),
        'keltner_atr_length': request.GET.get('keltnerAtrLength', '14'),
        'keltner_multiplier': request.GET.get('keltnerMultiplier', '2'),
    }
    
    # Fix default values for indicators
    for key, value in indicator_params.items():
        if value == '0':
            if key == 'ema':
                indicator_params[key] = '10'
            elif key == 'sma':
                indicator_params[key] = '10'
            elif key == 'hma':
                indicator_params[key] = '10'
            elif key == 'macd':
                indicator_params[key] = '12,26,9'
    
    logger.info(f"Unified SSE stream requested with data_types: {data_types}, timeframe: {timeframe}")
    
    response = StreamingHttpResponse(
        generate_unified_stream(data_types, timeframe, indicator_params),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


async def generate_unified_stream(data_types, timeframe, indicator_params):
    """
    Generate unified stream that yields different types of data separately.
    Each data type is processed independently with its own timing and yielded when ready.
    """
    # Define different refresh intervals for each data type (in seconds)
    refresh_intervals = {
        'dynamic': 1,      # Dynamic data every 1 second
        'static': 5,       # Static data every 5 seconds
        'indicators': 2    # Indicator data every 2 seconds
    }
    
    # Track last execution time for each data type
    last_execution = {data_type: 0 for data_type in data_types}
    
    # Create background tasks for each data type
    background_tasks = {}
    
    while True:
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Get tickers once per iteration
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            
            # Check which data types need to be fetched based on their intervals
            tasks_to_run = []
            
            for data_type in data_types:
                interval = refresh_intervals.get(data_type, 1)
                if current_time - last_execution[data_type] >= interval:
                    last_execution[data_type] = current_time
                    
                    if data_type == 'dynamic':
                        task = asyncio.create_task(
                            fetch_dynamic_data_with_timing(tickers, timeframe, data_type)
                        )
                    elif data_type == 'static':
                        task = asyncio.create_task(
                            fetch_static_data_with_timing(tickers, timeframe, data_type)
                        )
                    elif data_type == 'indicators':
                        task = asyncio.create_task(
                            fetch_indicators_data_with_timing(tickers, timeframe, indicator_params, data_type)
                        )
                    
                    tasks_to_run.append(task)
            
            # Process any completed background tasks
            for data_type in list(background_tasks.keys()):
                task = background_tasks[data_type]
                if task.done():
                    try:
                        result = await task
                        if result:
                            data_type_result, data, processing_time = result
                            if data:
                                yield f"data: {json.dumps({'type': data_type_result, 'data': data, 'timestamp': current_time, 'processing_time': processing_time}, cls=DjangoJSONEncoder)}\n\n"
                    except Exception as e:
                        logger.error(f"Error in background task for {data_type}: {str(e)}")
                        yield f"data: {json.dumps({'type': 'error', 'data_type': data_type, 'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
                    finally:
                        del background_tasks[data_type]
            
            # Start new background tasks
            for task in tasks_to_run:
                # Extract data type from task (we'll need to modify the functions to return this)
                # For now, we'll process them immediately but could be made truly background
                try:
                    result = await task
                    if result:
                        data_type_result, data, processing_time = result
                        if data:
                            yield f"data: {json.dumps({'type': data_type_result, 'data': data, 'timestamp': current_time, 'processing_time': processing_time}, cls=DjangoJSONEncoder)}\n\n"
                except Exception as e:
                    logger.error(f"Error processing task: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            
            # Small sleep to prevent busy waiting
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in generate_unified_stream: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)


async def fetch_dynamic_data_async(tickers, timeframe):
    """Fetch dynamic data for all tickers"""
    try:
        formatted_data = []
        for ticker in tickers:
            data = await retrieve_latest_data(ticker.ticker_symbol, timeframe)
            if data:
                formatted_data.append(data)
        
        return 'dynamic', formatted_data
    except Exception as e:
        logger.error(f"Error fetching dynamic data: {str(e)}")
        return 'dynamic', []


async def fetch_static_data_async(tickers, timeframe):
    """Fetch static data for all tickers"""
    try:
        formatted_data = []
        for ticker in tickers:
            data = await fetch_static_data(ticker.ticker_symbol, timeframe)
            if data:
                formatted_data.append(data)
        
        return 'static', formatted_data
    except Exception as e:
        logger.error(f"Error fetching static data: {str(e)}")
        return 'static', []


async def fetch_indicators_data_async(tickers, timeframe, indicator_params):
    """Fetch indicator data for all tickers"""
    try:
        formatted_data = []
        for ticker in tickers:
            data = await fetch_indicator_data(
                ticker.ticker_symbol,
                timeframe,
                indicator_params['ema'],
                indicator_params['sma'],
                indicator_params['hma'],
                indicator_params['macd'],
                indicator_params['supertrend_length'],
                indicator_params['supertrend_multiplier'],
                indicator_params['keltner_ema_length'],
                indicator_params['keltner_atr_length'],
                indicator_params['keltner_multiplier']
            )
            if data:
                formatted_data.append(data)
        
        return 'indicators', formatted_data
    except Exception as e:
        logger.error(f"Error fetching indicator data: {str(e)}")
        return 'indicators', []


async def fetch_dynamic_data_with_timing(tickers, timeframe, data_type):
    """Fetch dynamic data for all tickers with timing information"""
    start_time = asyncio.get_event_loop().time()
    try:
        formatted_data = []
        for ticker in tickers:
            data = await retrieve_latest_data(ticker.ticker_symbol, timeframe)
            if data:
                formatted_data.append(data)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        return data_type, formatted_data, processing_time
    except Exception as e:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Error fetching dynamic data: {str(e)}")
        return data_type, [], processing_time


async def fetch_static_data_with_timing(tickers, timeframe, data_type):
    """Fetch static data for all tickers with timing information"""
    start_time = asyncio.get_event_loop().time()
    try:
        formatted_data = []
        for ticker in tickers:
            data = await fetch_static_data(ticker.ticker_symbol, timeframe)
            if data:
                formatted_data.append(data)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        return data_type, formatted_data, processing_time
    except Exception as e:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Error fetching static data: {str(e)}")
        return data_type, [], processing_time


async def fetch_indicators_data_with_timing(tickers, timeframe, indicator_params, data_type):
    """Fetch indicator data for all tickers with timing information"""
    start_time = asyncio.get_event_loop().time()
    try:
        formatted_data = []
        for ticker in tickers:
            data = await fetch_indicator_data(
                ticker.ticker_symbol,
                timeframe,
                indicator_params['ema'],
                indicator_params['sma'],
                indicator_params['hma'],
                indicator_params['macd'],
                indicator_params['supertrend_length'],
                indicator_params['supertrend_multiplier'],
                indicator_params['keltner_ema_length'],
                indicator_params['keltner_atr_length'],
                indicator_params['keltner_multiplier']
            )
            if data:
                formatted_data.append(data)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        return data_type, formatted_data, processing_time
    except Exception as e:
        processing_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"Error fetching indicator data: {str(e)}")
        return data_type, [], processing_time


def dashboard(request):
    """Main dashboard view"""
    return render(request, 'maindas/dashboard.html')
