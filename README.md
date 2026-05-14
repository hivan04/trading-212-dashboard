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

## Performance Page 

Here, you can have a further insight into financial metrics, such as your portoflio's Sharpe Ratio, Maximum Drawdown, Compounded Annual Growth Rate (CAGR), Beta and Volatility.

It also pulls assumed data from yfinance to estimate the portfolo's value and drawdown 2§
