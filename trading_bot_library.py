# imports
import logging
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time
import pandas as pd
import numpy as np


# functions for whole project
def round_to_even(number):
    rounded_number = round(number)

    if rounded_number % 2 == 0:
        return rounded_number
    else:
        even_number = rounded_number - 1
        return even_number


def round_to_choice(x, choice):
    return choice * round(x / choice)


class BracketOrder(EWrapper, EClient):
    def __init__(self, symbol, sec_type, exchange, primary_exchange,
                 currency, action, quantity, limit_price, tp_price, sl_price):
        self.symbol = symbol
        self.sec_type = sec_type
        self.exchange = exchange
        self.primary_exchange = primary_exchange
        self.currency = currency
        self.action = action
        self.quantity = quantity
        self.limit_price = limit_price
        self.tp_price = tp_price
        self.sl_price = sl_price

        EClient.__init__(self, self)
        self.connect('127.0.0.1', 7497, 1)
        time.sleep(1)

        self.contract()

    def contract(self):
        contract = Contract()
        contract.symbol = self.symbol
        contract.secType = self.sec_type
        contract.exchange = self.exchange
        contract.primaryExchange = self.primary_exchange
        contract.currency = self.currency

        return contract

    def nextValidId(self, orderId: int):
        # This will be our main or "parent" order
        parent = Order()
        parent.orderId = orderId
        parent.action = self.action
        parent.orderType = "LMT"
        parent.totalQuantity = self.quantity
        parent.lmtPrice = self.limit_price
        parent.goodTillDate = '20231231-12:00:00'
        parent.tif = "GTD"
        parent.eTradeOnly = False
        parent.firmQuoteOnly = False
        # The parent and children orders will need this attribute set to False to prevent accidental executions.
        # The LAST CHILD will have it set to True,
        parent.transmit = False

        takeProfit = Order()
        takeProfit.orderId = parent.orderId + 1
        takeProfit.action = "SELL" if self.action == "BUY" else "BUY"
        takeProfit.orderType = "LMT"
        takeProfit.totalQuantity = self.quantity
        takeProfit.lmtPrice = self.tp_price
        takeProfit.parentId = parent.orderId
        takeProfit.goodTillDate = '20231231-12:00:00'
        takeProfit.tif = "GTD"
        takeProfit.eTradeOnly = False
        takeProfit.firmQuoteOnly = False
        takeProfit.transmit = False

        stopLoss = Order()
        stopLoss.orderId = parent.orderId + 2
        stopLoss.action = "SELL" if self.action == "BUY" else "BUY"
        stopLoss.orderType = "STP"
        # Stop trigger price
        stopLoss.auxPrice = self.sl_price
        stopLoss.totalQuantity = self.quantity
        stopLoss.parentId = parent.orderId
        stopLoss.goodTillDate = '20231231-12:00:00'
        stopLoss.tif = "GTD"
        stopLoss.eTradeOnly = False
        stopLoss.firmQuoteOnly = False
        # In this case, the low side order will be the last child being sent. Therefore, it needs to set this
        # attribute to True to activate all its predecessors
        stopLoss.transmit = True

        self.placeOrder(parent.orderId, self.contract(), parent)
        self.placeOrder(takeProfit.orderId, self.contract(), takeProfit)
        self.placeOrder(stopLoss.orderId, self.contract(), stopLoss)


class IbHistData(EClient, EWrapper):

    def __init__(self, symbol, sec_type, exchange, primary_exchange, currency, duration, barsize):
        self.symbol = symbol
        self.sec_type = sec_type
        self.exchange = exchange
        self.primary_exchange = primary_exchange
        self.currency = currency
        self.duration = duration
        self.barsize = barsize
        self.histbars = []

        EClient.__init__(self, self)

        # Connect to IB on init
        self.connect('127.0.0.1', 7497, 1)
        time.sleep(1)

    def nextValidId(self, orderId: int):
        contract = Contract()
        contract.symbol = self.symbol
        contract.secType = self.sec_type
        contract.exchange = self.exchange
        contract.primaryExchange = self.primary_exchange
        contract.currency = self.currency
        self.reqHistoricalData(orderId, contract, "", self.duration, self.barsize, "TRADES", 1, 1, 1, [])

    def historicalData(self, reqId, bar):
        bardict = {'reqid': reqId,
                   'datetime': bar.date,
                   'open': bar.open,
                   'high': bar.high,
                   'low': bar.low,
                   'close': bar.close,
                   'vol': bar.volume,
                   'barcount': bar.barCount}

        self.histbars.append(bardict)
        # print(self.histbars)

    def historicalDataEnd(self, reqId, start, end):
        print(f"End of HistoricalData")
        print(f"Start: {start}, End: {end}")

        self.disconnect()

    def error(self, reqId, errorCode, errorString):
        print("Error. Id: ", reqId, " Code: ", errorCode, " Msg: ", errorString)


class SmaStrategy:

    # this class will first have to check whether there is a signal for buy/sell from the historical dataset
    def __init__(self, df, roll_input, sma_percent, sl_input, tp_input, rounding_choice):

        self.df = df
        self.roll_input = roll_input
        self.sma_percent = sma_percent
        self.sl_input = sl_input
        self.tp_input = tp_input
        self.rounding_choice = rounding_choice

        self.add_signal_to_df()
        self.get_signal_from_df()

    def add_signal_to_df(self):
        self.df['sma'] = self.df['close'].rolling(self.roll_input).mean()
        self.df['sma_percent'] = self.sma_percent
        self.df['signal'] = np.where(self.df['sma'] > self.df['close'] * (1 + self.df['sma_percent']), True, False)

    def get_signal_from_df(self):
        if self.df.iloc[-1]['signal'] == [True]:
            print(True)
            return True
        else:
            print(False)
            return False

    def get_stop_loss_from_df(self):
        stop_loss = round_to_choice(self.df.iloc[-1]['close'] * (1 - self.sl_input), self.rounding_choice)
        return stop_loss

    def get_take_profit_from_df(self):
        take_profit = round_to_choice(self.df.iloc[-1]['close'] * (1 + self.tp_input), self.rounding_choice)
        return take_profit

    def get_limit_price_from_df(self):
        limit_price = round_to_choice(self.df.iloc[-1]['close'], self.rounding_choice)
        return limit_price


class TradingBot:

    def __init__(self, ticker, sec_type, exchange, primary_exchange, currency, duration, barsize,
                 roll_input, sma_percent, sl_input, tp_input, quantity, rounding_choice, sleep):

        self.ticker = ticker
        self.sec_type = sec_type
        self.exchange = exchange
        self.primary_exchange = primary_exchange
        self.currency = currency
        self.duration = duration
        self.barsize = barsize
        self.roll_input = roll_input
        self.sma_percent = sma_percent
        self.sl_input = sl_input
        self.tp_input = tp_input
        self.quantity = quantity
        self.rounding_choice = rounding_choice
        self.sleep = sleep

        self.limit_price = None
        self.sl_price = None
        self.tp_price = None

        # get historical data
        ib_hist_data = IbHistData(self.ticker, self.sec_type, self.exchange,
                                  self.primary_exchange, self.currency, self.duration, self.barsize)
        ib_hist_data.run()
        df = pd.DataFrame.from_records(ib_hist_data.histbars)

        # get signal from historical data df
        signal = SmaStrategy(df=df,
                             roll_input=self.roll_input,
                             sma_percent=self.sma_percent,
                             sl_input=self.sl_input,
                             tp_input=self.tp_input,
                             rounding_choice=self.rounding_choice)

        # decide whether to open a trade or not
        if signal.get_signal_from_df() == True:

            quantity = self.quantity
            limit_price = signal.get_limit_price_from_df()
            self.limit_price = limit_price
            print('limit price is: ', limit_price)
            tp_price = signal.get_take_profit_from_df()
            self.tp_price = tp_price
            print('tp price is: ', tp_price)
            sl_price = signal.get_stop_loss_from_df()
            self.sl_price = sl_price
            print('sl price is: ', sl_price)

            print('Order Initiated')
            order = BracketOrder(symbol=ticker,
                                 sec_type=sec_type,
                                 exchange=exchange,
                                 primary_exchange=primary_exchange,
                                 currency=currency,
                                 action='BUY',
                                 quantity=quantity,
                                 limit_price=limit_price,
                                 tp_price=tp_price,
                                 sl_price=sl_price)
            order.run()
            print('Order Submitted')

        else:
            print('No signal, no order submission')
            order = None

        time.sleep(self.sleep)


class AccountData(EWrapper, EClient):

    def __init__(self):
        self.acc_portfolio_bars = []
        self.acc_value_bars = []

        EClient.__init__(self, self)
        self.connect("127.0.0.1", 7497, 0)

        self.run()
        self.stop()

    def error(self, reqId, errorCode, errorString):
        print("Error: ", reqId, " ", errorCode, " ", errorString)

    def nextValidId(self, orderId):
        self.start()

    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        acc_portfolio_dict = {'contract': Contract,
                              'position': position,
                              'market_price': marketPrice,
                              'market_value': marketValue,
                              'average_cost': averageCost,
                              'unrealized_pnl': unrealizedPNL,
                              'realized_pnl': realizedPNL,
                              'account_name': accountName}

        self.acc_portfolio_bars.append(acc_portfolio_dict)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):

        acc_value_dict = {'key': key,
                          'val': val,
                          'currency': currency,
                          'accountName': accountName}

        self.acc_value_bars.append(acc_value_dict)

    def updateAccountTime(self, timeStamp: str):
        print("UpdateAccountTime. Time:", timeStamp)

    def accountDownloadEnd(self, accountName: str):
        print("AccountDownloadEnd. Account:", accountName)
        self.stop()

    def start(self):
        # Account number can be omitted when using reqAccountUpdates with single account structure
        self.reqAccountUpdates(True, "")

    def stop(self):
        self.reqAccountUpdates(False, "")
        self.done = True
        self.disconnect()
