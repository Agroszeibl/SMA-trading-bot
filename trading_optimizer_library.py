from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import pickle
import time
import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None  # default = 'warn'


class Position:

    def __init__(self, open_datetime, open_price, order_type, volume, sl, tp):
        self.open_datetime = open_datetime
        self.open_price = open_price
        self.order_type = order_type
        self.volume = volume
        self.sl = sl
        self.tp = tp
        self.Close_datetime = None
        self.Close_price = None
        self.profit = None
        self.cost = None
        self.status = 'open'

    def Close_position(self, Close_datetime, Close_price):
        self.Close_datetime = Close_datetime
        self.Close_price = Close_price
        self.cost = self.open_price * self.volume * 0.005
        self.profit = (self.Close_price - self.open_price) * self.volume if self.order_type == 'buy' \
            else (self.open_price - self.Close_price) * self.volume - self.cost
        self.status = 'Closed'

    def _asdict(self):
        return {
            'open_datetime': self.open_datetime,
            'open_price': self.open_price,
            'order_type': self.order_type,
            'volume': self.volume,
            'sl': self.sl,
            'tp': self.tp,
            'Close_datetime': self.Close_datetime,
            'Close_price': self.Close_price,
            'profit': self.profit,
            'status': self.status,
        }


class OptStrategy:

    def __init__(self, params, df):
        self.starting_balance = 0
        self.volume = 1
        self.positions = []
        self.df = df
        self.slinput = params['slinput']
        self.tpinput = params['tpinput']
        self.sma_roll = params['sma_roll']
        self.sma_percent = params['sma_percent']

    def get_positions_df(self):
        df = pd.DataFrame([position._asdict() for position in self.positions])
        if df.empty:
            return None
        else:
            df['pnl'] = df['profit'].cumsum() + self.starting_balance
            df['roll'] = self.sma_roll
            df['percent'] = self.sma_percent
            df['sl_percent'] = self.slinput
            df['tp_percent'] = self.tpinput
            return df

    def add_position(self, position):
        self.positions.append(position)

    def trading_allowed(self):
        for pos in self.positions:
            if pos.status == 'open':
                return False

        return True

    # for the current model, what are my signals?
    def generate_signal(self):
        self.df['sma'] = self.df['Close'].rolling(self.sma_roll).mean()
        self.df['signal_1'] = np.where(np.logical_or(self.df['sma'] > self.df['Close'] * (1 + self.sma_percent),
                                                     self.df['sma'] < self.df['Close'] * (1 - self.sma_percent)), True,
                                       False)
        self.df['signal_2'] = np.where(self.df['sma'] < self.df['Close'], "buy", "none")
        self.df['signal_3'] = np.where(self.df['signal_1'] == True, self.df['signal_2'], False)
        del self.df['signal_1']
        del self.df['signal_2']
        self.df['signal'] = self.df['signal_3']
        del self.df['signal_3']
        return self.df

    def run(self):

        self.generate_signal()

        for i, data in self.df.iterrows():

            if data.signal == 'buy' and self.trading_allowed():
                sl = data.Close * (1 - self.slinput)
                tp = data.Close * (1 + self.tpinput)
                self.add_position(Position(data.index, data.Close, data.signal, self.volume, sl, tp))

            elif data.signal == 'sell' and self.trading_allowed():
                sl = data.Close * (1 + self.slinput)
                tp = data.Close * (1 - self.tpinput)
                self.add_position(Position(data.index, data.Close, data.signal, self.volume, sl, tp))

            # changing SL and TP points to High / Low as in actuality it's that that triggers the sl or tp in live trading
            for pos in self.positions:
                if pos.status == 'open':
                    if (pos.sl >= data.Low and pos.order_type == 'buy'):
                        pos.Close_position(data.index, pos.sl)
                    elif (pos.sl <= data.High and pos.order_type == 'sell'):
                        pos.Close_position(data.index, pos.sl)
                    elif (pos.tp <= data.High and pos.order_type == 'buy'):
                        pos.Close_position(data.index, pos.tp)
                    elif (pos.tp >= data.Low and pos.order_type == 'sell'):
                        pos.Close_position(data.index, pos.tp)

        if self.get_positions_df() is None:
            no_trades = -0.00001
            return no_trades
        elif pd.isnull(self.get_positions_df()['pnl'].iloc[-1]) == True:
            no_trades_2 = -0.00001
            return no_trades_2
        else:

            # this returns profit
            df = self.get_positions_df()
            df_filtered = df.loc[df['pnl'].notnull()]
            profit = df_filtered['pnl'].iloc[-1]
            to_minimize = profit * -1

            return to_minimize


class StrategyTest:

    def __init__(self, df, starting_balance, volume, slinput, tpinput, sma_roll, sma_percent):
        self.starting_balance = starting_balance
        self.volume = volume
        self.positions = []
        self.df = df
        self.slinput = slinput
        self.tpinput = tpinput
        self.sma_roll = sma_roll
        self.sma_percent = sma_percent

    def get_positions_df(self):
        df = pd.DataFrame([position._asdict() for position in self.positions])
        if df.empty:
            return None
        else:
            df['pnl'] = df['profit'].cumsum() + self.starting_balance
            df['roll'] = self.sma_roll
            df['percent'] = self.sma_percent
            df['sl_percent'] = self.slinput
            df['tp_percent'] = self.tpinput
            return df

    def add_position(self, position):
        self.positions.append(position)

    def trading_allowed(self):
        for pos in self.positions:
            if pos.status == 'open':
                return False

        return True

    # for the current model, what are my signals?
    def generate_signal(self):
        self.df['sma'] = self.df['Close'].rolling(self.sma_roll).mean()
        self.df['signal_1'] = np.where(np.logical_or(self.df['sma'] > self.df['Close'] * (1 + self.sma_percent),
                                                     self.df['sma'] < self.df['Close'] * (1 - self.sma_percent)), True,
                                       False)
        self.df['signal_2'] = np.where(self.df['sma'] < self.df['Close'], "buy", "none")
        self.df['signal_3'] = np.where(self.df['signal_1'] == True, self.df['signal_2'], False)
        del self.df['signal_1']
        del self.df['signal_2']
        self.df['signal'] = self.df['signal_3']
        del self.df['signal_3']
        return self.df

    def run(self):

        self.generate_signal()

        for i, data in self.df.iterrows():

            if data.signal == 'buy' and self.trading_allowed():
                sl = data.Close * (1 - self.slinput)
                tp = data.Close * (1 + self.tpinput)
                self.add_position(Position(data.index, data.Close, data.signal, self.volume, sl, tp))

            elif data.signal == 'sell' and self.trading_allowed():
                sl = data.Close * (1 + self.slinput)
                tp = data.Close * (1 - self.tpinput)
                self.add_position(Position(data.index, data.Close, data.signal, self.volume, sl, tp))

            # changing SL and TP points to High / Low as in actuality it's that that triggers the sl or tp in live trading
            for pos in self.positions:
                if pos.status == 'open':
                    if (pos.sl >= data.Low and pos.order_type == 'buy'):
                        pos.Close_position(data.index, pos.sl)
                    elif (pos.sl <= data.High and pos.order_type == 'sell'):
                        pos.Close_position(data.index, pos.sl)
                    elif (pos.tp <= data.High and pos.order_type == 'buy'):
                        pos.Close_position(data.index, pos.tp)
                    elif (pos.tp >= data.Low and pos.order_type == 'sell'):
                        pos.Close_position(data.index, pos.tp)

        df = self.get_positions_df()

        if df is None:
            df_filtered = None
        else:
            df_filtered = df.loc[df['pnl'].notnull()]

        if df_filtered is None:
            # print('No trades opened, df is empty')
            returns_dict = {'percent_return': [0],
                            'percent_winning_trades': [0],
                            'slinput': [self.slinput],
                            'tpinput': [self.tpinput],
                            'sma_roll': [self.sma_roll],
                            'sma_percent': [self.sma_percent]}
            return returns_dict

        elif df_filtered.empty:
            # print('no trades closed, profit is: ', 0)
            returns_dict = {'percent_return': [0],
                            'percent_winning_trades': [0],
                            'slinput': [self.slinput],
                            'tpinput': [self.tpinput],
                            'sma_roll': [self.sma_roll],
                            'sma_percent': [self.sma_percent]}
            return returns_dict

        else:

            if df_filtered.loc[df_filtered['profit'] > 0].empty:
                # print('no winning trades, profit is negative')
                returns_dict = {'percent_return': [0],
                                'percent_winning_trades': [0],
                                'slinput': [self.slinput],
                                'tpinput': [self.tpinput],
                                'sma_roll': [self.sma_roll],
                                'sma_percent': [self.sma_percent]}
                return returns_dict

            else:
                # this returns profit
                percent_return = (df_filtered['pnl'].iloc[-1] / df_filtered['Close_price'].sum()) * 100
                percent_winning_trades = (len(df_filtered.loc[df_filtered['profit'] > 0]) / len(df_filtered)) * 100

                returns_dict = {'percent_return': [percent_return],
                                'percent_winning_trades': [percent_winning_trades],
                                'slinput': [self.slinput],
                                'tpinput': [self.tpinput],
                                'sma_roll': [self.sma_roll],
                                'sma_percent': [self.sma_percent]}

                print('trades opened, percent return vs mean closing price is: ', round(percent_return, 2), '%')
                print('percentage of winning trades is: ', round(percent_winning_trades, 2), '%')
                return returns_dict
