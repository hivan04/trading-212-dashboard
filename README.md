# Portfolio Dashboard - via. Streamlit

| Tab                   | Content                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| **Overview**    | KPI row (total value, invested, free cash, P&L, positions), portfolio donut chart, top holdings bar chart |
| **Performance** | Sharpe ratio, max drawdown, CAGR, annualised volatility; portfolio value line chart + drawdown chart      |
| **Holdings**    | Full positions table with quantity, avg price, current price, value, P&L, P&L %                           |
| **Dividends**   | Total / YTD / avg monthly KPIs, monthly bar chart, raw dividend table                                     |

**There is an option for looking at different timeframes to see portfolio's performance over various times:** 6mo/1y/2y/5y

# Key Features

## Overview Page 

Contains the overview of portfolio's performance, showing the heaviest weights (I set a condition to where any $w<0.01$) will be summed to the ```other''' category. You can also see your top holdings by value.

In terms of metrics, you can see your:

- Total Portfolio
- Amount Invested
- Cash Available
- Total PnL
- Total Return (in absolute value)
- Number of Active Open Positions

[!image](/Users/ivanhung/Documents/GitHub/trading-212-dashboard/images/1.png)

## Performance Page 

Here, you can have a further insight into financial metrics, such as your portoflio's Sharpe Ratio, Maximum Drawdown, Compounded Annual Growth Rate (CAGR), Beta and Volatility.

It also pulls data from yfinance to estimate the portfolo's value and drawdown to provide a further visual insight.

[!image](/Users/ivanhung/Documents/GitHub/trading-212-dashboard/images/2.png)

## Holdings 

This page shows all active holdnigs of the equities that are currentky being invested in and providing further information such as trading volume, current price, PnL and PnL as a %.

[!image](/Users/ivanhung/Documents/GitHub/trading-212-dashboard/images/3.png)

## Dividends

This page shows the accumualted dividends overtime and the company's which do the dividend payout. Here, it provides further insight to the amount of dividend paid per share and the date the dividend was recieved.

[!image](/Users/ivanhung/Documents/GitHub/trading-212-dashboard/images/4.png)
