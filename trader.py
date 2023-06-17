from trading_bot_library import TradingBot, AccountData
import pandas as pd
import pickle
import time

# optimization variable definitions

iterations = 250
symbol_optimization_max_attempts = 20
slinput_upper_stop = 0.05
tpinput_upper_stop = 0.05
sma_roll_upper_stop = 30
sma_percent_upper_stop = 0.05

# symbol variable definitions (dictionaries, lists)
tv_symbols = [['OTP', 'BET'],
              ['MOL', 'BET'],
              ['OPUS', 'BET'],
              ['4IG', 'BET'],
              ['RICHTER', 'BET'],
              ['MTELEKOM', 'BET'],
              ['BIF', 'BET'],
              ['ALR', 'GPW'],
              ['PKO', 'GPW'],
              ['ALE', 'GPW'],
              ['CIG', 'GPW'],
              ['EUR', 'GPW'],
              ['PKN', 'GPW'],
              ['TPE', 'GPW']
              ]

symbol_dictionary = {
    'OTP': {'ib_ticker': 'OTP',
            'ib_currency': 'HUF',
            'ib_primary_exchange': 'BUX',
            'ib_rounding_target': 2,
            'huf_conversion': 1},
    'MOL': {'ib_ticker': 'MOL',
            'ib_currency': 'HUF',
            'ib_primary_exchange': 'BUX',
            'ib_rounding_target': 2,
            'huf_conversion': 1},
    'RICHTER': {'ib_ticker': 'RICHTER',
                'ib_currency': 'HUF',
                'ib_primary_exchange': 'BUX',
                'ib_rounding_target': 5,
                'huf_conversion': 1},
    'OPUS': {'ib_ticker': 'OPUS',
             'ib_currency': 'HUF',
             'ib_primary_exchange': 'BUX',
             'ib_rounding_target': 0.2,
             'huf_conversion': 1},
    '4IG': {'ib_ticker': '4IG',
            'ib_currency': 'HUF',
            'ib_primary_exchange': 'BUX',
            'ib_rounding_target': 1,
            'huf_conversion': 1},
    'BIF': {'ib_ticker': 'BIF',
            'ib_currency': 'HUF',
            'ib_primary_exchange': 'BUX',
            'ib_rounding_target': 2,
            'huf_conversion': 1},
    'MTELEKOM': {'ib_ticker': 'MTELEKOM',
                 'ib_currency': 'HUF',
                 'ib_primary_exchange': 'BUX',
                 'ib_rounding_target': 0.5,
                 'huf_conversion': 1},
    'ALR': {'ib_ticker': 'ALR',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.05,
            'huf_conversion': 0.012},
    'PKO': {'ib_ticker': 'PKO',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.05,
            'huf_conversion': 0.012},
    'ALE': {'ib_ticker': 'ALE',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.005,
            'huf_conversion': 0.012},
    'CIG': {'ib_ticker': 'CIG',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.005,
            'huf_conversion': 0.012},
    'EUR': {'ib_ticker': 'EUR',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.05,
            'huf_conversion': 0.012},
    'PKN': {'ib_ticker': 'PKN',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.02,
            'huf_conversion': 0.012},
    'TPE': {'ib_ticker': 'TPE',
            'ib_currency': 'PLN',
            'ib_primary_exchange': 'WSE',
            'ib_rounding_target': 0.01,
            'huf_conversion': 0.012}
}

# misc variable definitions
# group these later into a bucket?
optim_dictionary = {}
df_tv = None
sec_type = 'STK'
exchange = 'SMART'
currency = 'HUF'
duration = '1 D'
barsize = '1 min'

if __name__ == '__main__':

    # Read dictionary pkl file
    with open('optim_dictionary.pkl', 'rb') as fp:
        optim_dictionary = pickle.load(fp)
        print(optim_dictionary)

    # run trading loop
    while True:

        for tv_symbol in tv_symbols:

            if optim_dictionary[tv_symbol[0]]['initiation_flag']:
                print('initiate bot for:', tv_symbol)
                print('symbol dictionary is: ', symbol_dictionary[tv_symbol[0]])

                # get account data
                account_data = AccountData()
                df_account_data = pd.DataFrame.from_records(account_data.acc_value_bars)
                df_huf = df_account_data.loc[
                    df_account_data['key'].eq('CashBalance') & df_account_data['currency'].eq('HUF')]
                huf_balance = float(df_huf['val'].iloc[0])

                if huf_balance < 500000:
                    print('cash balance too low for trading')

                else:
                    quantity = round((huf_balance * 0.01) / \
                                     (optim_dictionary[tv_symbol[0]]['slinput'] * (
                                             optim_dictionary[tv_symbol[0]]['average_price'] /
                                             symbol_dictionary[tv_symbol[0]]['huf_conversion'])))

                    bot = TradingBot(ticker=symbol_dictionary[tv_symbol[0]]['ib_ticker'],
                                     sec_type=sec_type,
                                     exchange='SMART',
                                     primary_exchange=symbol_dictionary[tv_symbol[0]]['ib_primary_exchange'],
                                     currency=symbol_dictionary[tv_symbol[0]]['ib_currency'],
                                     duration=duration,
                                     barsize=barsize,
                                     roll_input=optim_dictionary[tv_symbol[0]]['sma_roll'],
                                     sma_percent=optim_dictionary[tv_symbol[0]]['sma_percent'],
                                     sl_input=optim_dictionary[tv_symbol[0]]['slinput'],
                                     tp_input=optim_dictionary[tv_symbol[0]]['tpinput'],
                                     quantity=quantity,
                                     sleep=0,
                                     rounding_choice=symbol_dictionary[tv_symbol[0]]['ib_rounding_target'])
            else:
                print('Not initiating bot for: ', tv_symbol)

        time.sleep(60)
