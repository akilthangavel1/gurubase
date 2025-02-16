from django.shortcuts import render
from .fyers_optionchain import get_option_chain_data, get_option_quotes
from django.http import JsonResponse
import datetime



def table_stream(request):
    return render(request, "dasoptions/trade_options.html", {})


def get_data_by_symbol(data, symbol):
    for item in data.get('d', []):
        if item['n'] == symbol:
            return item
    return None



def option_chain_view(request):
    if request.method == 'POST':
        stock_name = request.POST.get('stock_name')
        strike_price = request.POST.get('strike_price')
        date_filter = request.POST.get('date_filter')

        try:
            date_filter = datetime.datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            date_filter = None 

        option_chain_data = get_option_chain_data(stock_name)

        options_chain = option_chain_data['data']['optionsChain']
        symbol_quotes = "NSE:SBIN-EQ"
        for option in options_chain:
            symbol_quotes+= "," +(option["symbol"])
        symbol_quotes_results = get_option_quotes(symbol_quotes)
        # print(symbol_quotes_results)

        options_chain_filtered = []
        for option in options_chain:
            if option["option_type"] == "PE" or option["option_type"] == "CE":
                options_chain_filtered.append(option)

        result_optionchain = []
        for option in options_chain_filtered:
            quote_data = get_data_by_symbol(symbol_quotes_results, option["symbol"])
            # print(quote_data['v'])
            try:
                result_optionchain.append({
                    'ticker': option["symbol"],
                    'xch': quote_data['v']['exchange'],
                    'ltp': option["ltp"],
                    'qty': 0,
                    'chg': option["ltpch"],
                    'percent_chg': option["ltpchp"],
                    'bid_qty': 0,
                    'bid': option["bid"],
                    'open': quote_data['v']['open_price'],
                    'p_close': quote_data['v']['prev_close_price'],
                    'low': quote_data['v']['low_price'],
                    'high': quote_data['v']['high_price'],
                    'avg_price': 0,
                    't_volume': option["volume"],
                    'total_value': 0,
                    'oi': option["oi"],
                    'no_of_contracts': 0,
                    'strike_price': option["strike_price"],
                    'exp_date': 0,
                    'option_type': option["option_type"],
                    'p_open': 0,
                    'oi_combined_fut': 0,
                    'five_day_avg_vol': 0,
                    'calculated_column1': 0,
                    'calculated_column2': 0,
                    'calculated_column3': 0,
                })
            except:
                print("ERROR")

        # Return the data as JSON
        return JsonResponse({'data': result_optionchain})

    return JsonResponse({'error': 'Invalid request method'}, status=400)