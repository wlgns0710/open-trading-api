# KIS Auto Trading Final Project

This repository contains the KIS auto-trading final project for the AI and Financial Engineering course.

The main project is located in:

```text
final_project/kis_auto_trading/
```

## Project Overview

This project implements a mock auto-trading system using the Korea Investment & Securities Open API.

The system connects to the KIS mock trading environment, issues an OAuth access token, retrieves stock price data and account balance, applies a moving average crossover strategy, checks risk management conditions, and records the trading decision process.

In addition, the project includes a real mock trading test that verifies both BUY and SELL order requests in the KIS virtual trading environment.

## Main Features

* OAuth access token issuance
* Current stock price inquiry
* Mock account balance inquiry
* Daily stock price data inquiry
* 5-day / 20-day moving average crossover strategy
* BUY / SELL / HOLD signal generation
* Risk management before order execution
* DRY_RUN order flow test
* Real mock trading BUY / SELL order request test
* Trading result logging to CSV
* Error handling for API rate limits, account input issues, market close, and order failures

## Project Structure

```text
final_project/kis_auto_trading/
├── main.py
├── trader.py
├── kis_api.py
├── strategy.py
├── risk_manager.py
├── logger.py
├── requirements.txt
├── .env.example
├── .gitignore
├── images/
└── README.md
```

## How to Run

Move to the project directory.

```bash
cd final_project/kis_auto_trading
```

Install required packages.

```bash
pip install -r requirements.txt
```

Create a `.env` file by referring to `.env.example`.

Run the moving-average-based auto-trading flow.

```bash
python main.py
```

Run the real mock trading BUY / SELL order test.

```bash
python trader.py
```

## Detailed Documentation

For implementation details, execution results, screenshots, error handling, and test records, please refer to the project README:

```text
final_project/kis_auto_trading/README.md
```

## Note

This project was implemented and tested in the KIS mock trading environment.
Actual investment trading was not performed.
