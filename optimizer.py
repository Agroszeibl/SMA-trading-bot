from trading_optimizer_library import OptStrategy, StrategyTest
import pandas as pd
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import pickle
import time
# https://github.com/StreamAlpha/tvdatafeed
from tvDatafeed import TvDatafeed, Interval
import csv

# optimization variable definitions

iterations = 250
symbol_optimization_max_attempts = 25
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

    # running optimizer for all symbols in dictionary
    for tv_symbol in tv_symbols:

        # variables for optimization attempts
        optim_attempts = 1
        initiation_flag = False

        # added this loop to attempt a few optim runs on a symbol
        while optim_attempts < symbol_optimization_max_attempts + 1 and initiation_flag == False:

            # loop level variables
            trials = Trials()
            best = None

            # importing data

            # get credentials for tradingview
            username = 'amusedHope9510e'
            password = 'Delta1234'
            tv = TvDatafeed(username=username, password=password)

            symbol = tv_symbol[0]
            exchange = tv_symbol[1]

            df_tv = tv.get_hist(symbol, exchange, interval=Interval.in_1_minute, n_bars=5000)
            df_tv.rename(columns={'close': 'Close', 'low': 'Low', 'high': 'High'}, inplace=True)
            train_test_split_point = int(round(len(df_tv) / 3))
            df_train = df_tv.iloc[:train_test_split_point, :]
            df_test = df_tv.iloc[train_test_split_point:train_test_split_point * 2, :]
            df_validate = df_tv.iloc[train_test_split_point * 2:, :]


            # running optimization symbol by symbol
            # first run training on df_train
            # test which trained model performs best on df_test
            # validate the results of best df_test model on df_validate

            # create functions for optimizer
            def strategy_objective(params):
                object_to_optimize = OptStrategy(params=params,
                                                 df=df_train)
                return object_to_optimize.run()


            def objective(params):
                return {'loss': strategy_objective(params),
                        'status': STATUS_OK,
                        'eval_time': time.time(),
                        'other_stuff': {'type': None, 'value': [0, 1, 2]},
                        'attachments': {'time_module': pickle.dumps(time.time)}
                        }


            # parameters for optimization
            space = {'sma_roll': hp.randint('sma_roll', 1, sma_roll_upper_stop),
                     'slinput': hp.uniform('slinput', 0, slinput_upper_stop),
                     'tpinput': hp.uniform('tpinput', 0, tpinput_upper_stop),
                     'sma_percent': hp.uniform('sma_percent', 0, sma_percent_upper_stop)}

            #############################################################
            # first run training on df_train ############################
            #############################################################
            print('running optimization for: ', tv_symbol)
            best = fmin(fn=objective,
                        space=space,
                        algo=tpe.suggest,
                        trials=trials,
                        max_evals=iterations)

            #############################################################
            # test which trained model performs best on df_test #########
            #############################################################

            # create dataframe for testing from trials dataset
            tpe_results = pd.DataFrame({'score': [x['loss'] for x in trials.results],
                                        'sma_roll': trials.idxs_vals[1]['sma_roll'],
                                        'slinput': trials.idxs_vals[1]['slinput'],
                                        'tpinput': trials.idxs_vals[1]['tpinput'],
                                        'sma_percent': trials.idxs_vals[1]['sma_percent']})
            tpe_results.sort_values(by=['score'], inplace=True)

            tpe_results = tpe_results.loc[tpe_results['score'] < -0.00001]
            tpe_results = tpe_results.reset_index()
            tpe_results.head()

            # run strategy test on test_df for each row in tpe_results where score < -0.00001
            # create a dataframe which contains for a given set

            test_results_df = None

            for index, row in tpe_results.iterrows():

                tester_slinput = row['slinput']
                tester_tpinput = row['tpinput']
                tester_sma_roll = int(row['sma_roll'])
                tester_sma_percent = row['sma_percent']

                # backtest optimization on test dataset
                strategy_test = StrategyTest(df=df_test,
                                             starting_balance=0,
                                             volume=1,
                                             slinput=tester_slinput,
                                             tpinput=tester_tpinput,
                                             sma_roll=tester_sma_roll,
                                             sma_percent=tester_sma_percent)

                test_results = strategy_test.run()

                if test_results_df is None:
                    test_results_df = pd.DataFrame.from_dict(test_results)
                else:
                    iter_df = pd.DataFrame.from_dict(test_results)
                    test_results_df = pd.concat([test_results_df, iter_df], ignore_index=True)

            # section to get best returns params. Need to return a None df is best return is 0 or less

            if tpe_results.empty:
                max_return = 0.0
            else:
                max_return = test_results_df['percent_return'].max()

            if max_return == 0.0:
                best_returns_params = None
            else:
                best_returns_params = test_results_df.loc[test_results_df['percent_return'] == max_return]

            if best_returns_params is None:
                best_percent_return = 0
                best_percent_winning_trades = 0

            else:
                best_percent_return = best_returns_params['percent_return'].iat[0]
                best_percent_winning_trades = best_returns_params['percent_winning_trades'].iat[0]

            initiation_flag_test = best_percent_return > 0 and best_percent_winning_trades > 80

            #############################################################
            # validate the results of best df_test model on df_validate #
            #############################################################

            if initiation_flag_test == True:

                val_slinput = best_returns_params['slinput'].iat[0]
                val_tpinput = best_returns_params['tpinput'].iat[0]
                val_sma_roll = best_returns_params['sma_roll'].iat[0]
                val_sma_percent = best_returns_params['sma_percent'].iat[0]

                # backtest optimization on test dataset
                print('running validation. Following print is showing validation results.')
                strategy_validate = StrategyTest(df=df_validate,
                                                 starting_balance=0,
                                                 volume=1,
                                                 slinput=val_slinput,
                                                 tpinput=val_tpinput,
                                                 sma_roll=val_sma_roll,
                                                 sma_percent=val_sma_percent)

                val_results = strategy_validate.run()
                val_results_df = pd.DataFrame.from_dict(val_results)

            # just a bunch of logic to handle exceptions and errors
            else:
                val_results_df = None

            if val_results_df is None:
                initiation_flag = False
            else:
                initiation_flag = val_results_df['percent_return'].iat[0] > 0 and \
                                  val_results_df['percent_winning_trades'].iat[0] > 80

            if val_results_df is None:
                optim_dictionary.update({tv_symbol[0]: {'sma_roll': 0,
                                                        'slinput': 0,
                                                        'tpinput': 0,
                                                        'sma_percent': 0,
                                                        'initiation_flag': initiation_flag,
                                                        'average_price': df_tv['Close'].mean()}})

            else:
                optim_dictionary.update({tv_symbol[0]: {'sma_roll': val_results_df['sma_roll'].iat[0],
                                                        'slinput': val_results_df['slinput'].iat[0],
                                                        'tpinput': val_results_df['tpinput'].iat[0],
                                                        'sma_percent': val_results_df['sma_percent'].iat[0],
                                                        'initiation_flag': initiation_flag,
                                                        'average_price': df_tv['Close'].mean()}})

            optim_attempts += 1
            print(optim_dictionary)

            # save dictionary to person_data.pkl file
            with open('optim_dictionary.pkl', 'wb') as fp:
                pickle.dump(optim_dictionary, fp)
                print('dictionary saved successfully to file')