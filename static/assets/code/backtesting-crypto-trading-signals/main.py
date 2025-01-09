import json
import ccxt
from ccxt.base.errors import BadSymbol
import pandas as pd
import csv
import numpy as np
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import matplotlib.cm as cm

# Takes the Telegram JSON file and parses it
def format_data():
    with open('data/telegram_data.json', 'r') as file:
        all_messages = json.load(file)

    trade_list = []

    # Sample message data
    for trade in all_messages['messages']:
        if not "reply_to_message_id" in trade:
            message_data = trade

            # Join all text in the list
            combined_text = ""

            for item in trade['text']:
                if isinstance(item, dict) and "text" in item:
                    combined_text += item["text"]
                elif isinstance(item, str):
                    combined_text += item

            # Extract relevant information
            symbol_match = re.search(r"#(\w+)", combined_text)
            symbol = symbol_match.group(1).replace('USDTPERP', '/USDT') if symbol_match else None

            direction_match = re.search(r"(Long|Short)", combined_text, re.IGNORECASE)
            direction = direction_match.group(1).capitalize() if direction_match else None

            entry_price_match = re.search(r"Entry:\s([\d.]+)", combined_text)
            entry_price = float(entry_price_match.group(1)) if entry_price_match else None

            targets_matches = re.findall(r"Target\s\d\s*:\s([\d.]+)", combined_text)
            # Common ratio
            r = 0.5
            # Calculate the first term (a) for the sum to be 1
            initial_percentage = 1 / (1 + r + r ** 2 + r ** 3)

            # Initialize the list of targets with exponential percentages
            targets = []
            current_percentage = initial_percentage

            # Generate the targets with decreasing percentages
            for target in targets_matches:
                targets.append({
                    "price": float(target),
                    "achieved": "no",
                    "percentage": current_percentage
                })
                current_percentage *= r  # Decrease the percentage exponentially

            stop_loss_match = re.search(r"Stop-[Ll]oss:\s([\d.]+)", combined_text, re.IGNORECASE)
            stop_loss = float(stop_loss_match.group(1)) if stop_loss_match else None

            leverage_match = re.search(r"Leverage:\s(\d+)x", combined_text)
            leverage = int(leverage_match.group(1)) if leverage_match else None

            # Extract signal time
            signal_time = message_data.get("date")
            if symbol and signal_time and direction and leverage and entry_price and stop_loss and targets:
                # Create the JSON structure
                trade_data = {
                    "pair": symbol,
                    "signal_time": signal_time,
                    "direction": direction,
                    "leverage": leverage,
                    "entry": {
                        "price": entry_price,
                        "achieved": "no"
                    },
                    "stop_loss": {
                        "price": stop_loss,
                        "achieved": "no"
                    },
                    "targets": targets
                }

                trade_list.append(trade_data)

    # Convert to JSON
    trade_data_json = json.dumps(trade_list, indent=4)

    # Write to a JSON file
    with open('trades/trades.json', 'w') as json_file:
        json_file.write(trade_data_json)


# Simulates the signals in the market with the ccxt library
def simulate_trades():
    # Load JSON data
    with open('trades/trades.json', 'r') as file:
        signals_data = json.load(file)

    exchange = ccxt.bitget()  # Replace with your exchange

    def fetch_historical_data(pair, since, timeframe):
        try:
            ohlcv = exchange.fetch_ohlcv(pair, timeframe, since)
        except BadSymbol:
            print("BadSymbol")
            return None
        else:
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df

    def check_entry(signal):
        entry_timestamps_1h = fetch_historical_data(signal['pair'], exchange.parse8601(signal['signal_time']), "1h")
        if entry_timestamps_1h is None:
            return False
        for index, row in entry_timestamps_1h.iterrows():
            # Check if the entry price was reached
            if row['low'] <= signal["entry"]["price"] <= row['high']:
                entry_timestamps_1m = fetch_historical_data(signal['pair'],
                                                            exchange.parse8601(row['timestamp'].isoformat()), "1m")
                for index, row in entry_timestamps_1m.iterrows():
                    if row['low'] <= signal["entry"]["price"] <= row['high']:
                        if row['timestamp'].isoformat() >= signal["signal_time"]:
                            signal["entry"]["time_achieved"] = row['timestamp'].isoformat()
                            signal["entry"]["achieved"] = 'yes'
                            return True
        return False

    def check_sl_or_tp(signal):
        timestamps_after_entry_1h = fetch_historical_data(signal['pair'],
                                                          exchange.parse8601(signal['entry']['time_achieved']), "1h")

        if timestamps_after_entry_1h is None:
            return False

        for index, row in timestamps_after_entry_1h.iterrows():
            trail_stop_loss(signal)
            targets = [target for target in signal["targets"] if target["achieved"] == "no"]
            # Check if all TPs are reached before the SL
            if not targets:
                return True, signal["targets"][-1]["time_achieved"]

            # Long
            elif signal["direction"] == "Long":
                sl_achieved = row['low'] <= signal["stop_loss"]["price"]
                tp_achieved = any([row['high'] >= target["price"] for target in targets])

                if sl_achieved and tp_achieved:

                    timestamps_after_entry_1m = fetch_historical_data(signal['pair'],
                                                                      exchange.parse8601(row['timestamp'].isoformat()),
                                                                      "1m")
                    stop_loss_time = \
                    timestamps_after_entry_1m[timestamps_after_entry_1m['low'] <= signal["stop_loss"]["price"]][
                        'timestamp'].iloc[0].isoformat()
                    for target in targets:
                        if row['high'] >= target["price"]:
                            tp_time = timestamps_after_entry_1m[timestamps_after_entry_1m['high'] >= target["price"]][
                                'timestamp'].iloc[0].isoformat()
                        else:
                            continue
                        if stop_loss_time > tp_time:
                            target["achieved"] = "yes"
                            target["time_achieved"] = tp_time
                    signal["stop_loss"]["achieved"] = "yes"
                    signal["stop_loss"]["time_achieved"] = stop_loss_time
                    return True, stop_loss_time

                elif sl_achieved:
                    signal["stop_loss"]["achieved"] = "yes"
                    signal["stop_loss"]["time_achieved"] = row['timestamp'].isoformat()
                    return True, signal["stop_loss"]["time_achieved"]

                elif tp_achieved:
                    for target in targets:
                        if row["high"] >= target["price"]:
                            target["achieved"] = "yes"
                            target["time_achieved"] = row['timestamp'].isoformat()

            # Short
            elif signal["direction"] == "Short":
                sl_achieved = row['high'] >= signal["stop_loss"]["price"]
                tp_achieved = any([row['low'] <= target['price'] for target in targets])

                if sl_achieved and tp_achieved:
                    timestamps_after_entry_1m = fetch_historical_data(signal['pair'],
                                                                      exchange.parse8601(row['timestamp'].isoformat()),
                                                                      "1m")
                    stop_loss_time = \
                    timestamps_after_entry_1m[timestamps_after_entry_1m['high'] >= signal["stop_loss"]["price"]][
                        'timestamp'].iloc[0].isoformat()
                    for target in signal["targets"]:
                        for target in targets:
                            if row['low'] <= target["price"]:
                                tp_time = \
                                timestamps_after_entry_1m[timestamps_after_entry_1m['low'] <= target["price"]][
                                    'timestamp'].iloc[0].isoformat()
                            else:
                                continue
                            if stop_loss_time > tp_time:
                                target["achieved"] = "yes"
                                target["time_achieved"] = tp_time
                    signal["stop_loss"]["achieved"] = "yes"
                    signal["stop_loss"]["time_achieved"] = stop_loss_time
                    return True, stop_loss_time

                elif sl_achieved:
                    signal["stop_loss"]["achieved"] = "yes"
                    signal["stop_loss"]["time_achieved"] = row['timestamp'].isoformat()
                    return True, signal["stop_loss"]["time_achieved"]

                elif tp_achieved:
                    for target in targets:
                        if row["low"] <= target["price"]:
                            target["achieved"] = "yes"
                            target["time_achieved"] = row['timestamp'].isoformat()

        return False, None

    def trail_stop_loss(signal):
        # Count the number of achieved targets
        achieved_targets = [target for target in signal['targets'] if target['achieved'] == 'yes']
        num_achieved_targets = len(achieved_targets)

        # Update the stop loss based on the number of achieved targets
        if num_achieved_targets == 1:
            # Move SL to entry price (breakeven)
            signal['stop_loss']['price'] = signal['entry']['price']
        elif num_achieved_targets == 2:
            # Move SL to the first target price
            first_target_price = signal['targets'][0]['price']
            signal['stop_loss']['price'] = first_target_price
        elif num_achieved_targets == 3:
            # Move SL to the first target price
            first_target_price = signal['targets'][1]['price']
            signal['stop_loss']['price'] = first_target_price
        elif num_achieved_targets == 4:
            # Move SL to the first target price
            first_target_price = signal['targets'][2]['price']
            signal['stop_loss']['price'] = first_target_price

    def simulate_trade(signal):
        entered = check_entry(signal)

        if entered:
            close_trade, closing_time = check_sl_or_tp(signal)
            if close_trade:
                signal["result"] = {
                    "close_time": closing_time,
                    "roi": ""
                }
                return True
            if not close_trade:
                print("still open")
                return False
        else:
            print("not entered")
            return False

    def calculate_roi(signal):
        entry_price = signal['entry']['price']
        stop_loss_price = signal['stop_loss']['price']
        direction = signal['direction']
        total_percentage = 0.0

        # Calculate ROI for each achieved target
        for target in signal['targets']:
            if target['achieved'] == 'yes':
                target_price = target['price']
                percentage_sold = target['percentage']
                if direction == 'Long':
                    roi = ((target_price - entry_price) / entry_price) * 100 * percentage_sold
                elif direction == 'Short':
                    roi = ((entry_price - target_price) / entry_price) * 100 * percentage_sold
                total_percentage += roi

        # Check if stop loss was hit and calculate its ROI
        if signal['stop_loss']['achieved'] == 'yes':
            percentage_not_sold = len([target for target in signal['targets'] if target['achieved'] == "no"]) / len(
                signal["targets"])
            if direction == 'Long':
                stop_loss_roi = ((stop_loss_price - entry_price) / entry_price) * 100 * percentage_not_sold
            elif direction == 'Short':
                stop_loss_roi = ((entry_price - stop_loss_price) / entry_price) * 100 * percentage_not_sold
            total_percentage += stop_loss_roi

        return round(total_percentage * signal["leverage"], 2)

    # Open the file once at the beginning
    with open(f"result_movingtarget_decrexp.csv", "w", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(["Profit", "Closed at"])

        # Simulate trades for all signals
        for signal in signals_data:
            print(f"{signals_data.index(signal)}/{len(signals_data)}")
            signal["signal_time"] = pd.to_datetime(signal["signal_time"]).isoformat()
            trade_finished = simulate_trade(signal)
            if trade_finished:
                roi = calculate_roi(signal)
                signal["result"]["roi"] = roi
                writer.writerow([signal["result"]["roi"], signal["result"]["close_time"]])
            else:
                for anti_signal in signals_data[signals_data.index(signal):]:
                    if signal['pair'] == anti_signal['pair'] and signal["direction"] != anti_signal['direction']:
                        roi = calculate_roi(signal)
                        signal["result"] = {
                            "close_time": anti_signal['signal_time'],
                            "roi": roi
                        }
                        break


# Analyses the backtest result and plots information rich graphs
def plot_graphs():
    # Path to the current directory in which the CSV files are located
    directory_path = '/results/'
    # list all files in path
    file_names = os.listdir(directory_path)

    # filter by csv file type
    csvs = [file for file in file_names if file.endswith('.csv')]

    grouped_dfs = []
    dfs = []

    for csv in csvs:
        df = pd.read_csv(csv)

        # Scale Profit column
        df['Profit'] = df['Profit'] / 100

        # Convert 'Closed at' column to datetime
        df['Closed at'] = pd.to_datetime(df['Closed at'])

        # Strip the time part to keep only the date
        df['Closed at'] = df['Closed at'].dt.date

        dfs.append(df)

    for df in dfs:
        # Group by 'Closed at' date and calculate mean
        grouped_df = df.groupby('Closed at').mean().reset_index()

        # Calculate rolling mean of 'Profit' with a window of 7 days
        grouped_df['Rolling Profit'] = grouped_df['Profit'].rolling(window=7).mean()

        # Append the results to the lists
        grouped_dfs.append(grouped_df)

    for csv in csvs:
        index = csvs.index(csv)

        plt.figure(figsize=(20, 10))
        plt.plot(grouped_dfs[index]['Closed at'], grouped_dfs[index]['Profit'], label='ROI per trade', alpha=0.5)
        plt.plot(grouped_dfs[index]['Closed at'], grouped_dfs[index]['Rolling Profit'], label="1W Moving Average",
                 color='red')
        plt.axhline(y=grouped_dfs[index]['Profit'].mean(), color='red', linestyle=':',
                    label=f"Mean ({round(grouped_dfs[index]['Profit'].mean(), 4)})")
        plt.axhline(y=0, color='black', linestyle='--')

        plt.ylim([-1, 1])
        # Set the locator for the x-axis to locate months
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.MonthLocator())

        plt.xticks(rotation=20, fontsize=8)
        plt.title(
            f'Average ROI per Trade across {dfs[index]["Profit"].shape[0]} Trades within {dfs[index]["Closed at"].nunique()} Trading Days',
            fontsize=16)

        plt.legend()
        plt.grid(True, alpha=0.5)
        plt.show()

    INITIAL = 1000
    MARGIN = 0.02
    TAKER_FEE = 0.001  # 0.1%
    FUNDING_FEE = 0.0002  # 0.02%
    LEVERAGE = 10
    AVG_FUNDING_CYCLES_PER_TRADE = 3  # 24h Avg. Trade Length

    # WITH FEES
    for fees_df in dfs:
        # Initialize the first balance value
        initial_balance = INITIAL + (INITIAL * MARGIN * fees_df.loc[0, 'Profit'])
        # Subtract taker fee for the first trade
        initial_balance -= initial_balance * TAKER_FEE
        fees_df.loc[0, 'Balance'] = initial_balance

        # Iterate through the DataFrame starting from the second row
        for i in range(1, len(fees_df)):
            previous_balance = fees_df.loc[i - 1, 'Balance']
            profit = fees_df.loc[i, 'Profit']

            # Calculate new balance - Calculating the funding fees based on position size and trade duration
            new_balance = previous_balance + (previous_balance * MARGIN * profit - (previous_balance * MARGIN * LEVERAGE * FUNDING_FEE * AVG_FUNDING_CYCLES_PER_TRADE) - (previous_balance * MARGIN * TAKER_FEE))
            fees_df.loc[i, 'Balance'] = new_balance

        # Calculate daily returns
        daily_roi = np.diff(fees_df['Balance']) / fees_df['Balance'][:-1]

        # Calculate average daily return
        avg_daily_roi = np.mean(daily_roi) * 100

        # Calculate standard deviation of daily returns
        volatility = np.std(daily_roi) * 100

        # Assumed risk-free rate (in percent)
        risk_free_rate = 3 / 365

        # Calculate the Sharpe Ratio
        sharpe_ratio = (avg_daily_roi - risk_free_rate) / volatility

        # Calculate the running maximum of the balance
        running_max = fees_df['Balance'].cummax()

        # Calculate the drawdown
        drawdown = (running_max - fees_df['Balance']) / running_max

        # Calculate the maximum drawdown
        max_drawdown = drawdown.max()

        # Convert the maximum drawdown to a percentage
        max_drawdown_percent = max_drawdown * 100

        # Calculate Composite Score
        score = (sharpe_ratio * avg_daily_roi) / (volatility * max_drawdown)

    # colors for graphs
    N = len(dfs)  # number of lines
    x = np.array([0, 1])
    theta = np.linspace(0, np.pi / 2, N)

    discr = np.linspace(0, 1, N)
    # create N colors from the colormap
    colors = cm.hsv(discr)

    # Create a custom legend entry
    custom_legend = (
        f"Starting Balance = {INITIAL}\n"
        f"Margin per Trade = {MARGIN * 100}%\n"
        f"Taker Fee = {TAKER_FEE * 100}%\n"
        f"Funding Fee = {FUNDING_FEE * 100}%\n"
        f"Leverage = {LEVERAGE}x\n"
        f"Avg. Trade Duration = {AVG_FUNDING_CYCLES_PER_TRADE * 8}h\n"
        f"Sharpe Ratio: {sharpe_ratio:.2f}\n"
        f"Avg. Daily ROI = {avg_daily_roi:.2f}%\n"
        f"Volatility = {volatility:.2f}%\n"
        f"Max Drawdown: {max_drawdown_percent:.2f}%\n"
        f"Composite Score: {score:.4f}"
    )

    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(20, 10))

    for ind, fees_df in enumerate(dfs):
        # Extract the base name of the file without the extension
        file_label = os.path.splitext(os.path.basename(csvs[ind]))[0]
        # Plot the data
        ax.plot(fees_df.index, fees_df['Balance'], label=file_label, color=colors[ind])

    # Set plot  labels
    ax.set_title(
        'Account Balance along each trade with 4 Exponentially Decreasing Take Profits and a Moving Target Stop Loss Strategy')
    ax.set_xlabel("Number of Trades")
    ax.set_ylabel("Balance")

    # Add the first legend for the plot labels
    first_legend = ax.legend(loc='upper left')

    # Add the second legend for the custom parameters
    # We need to create a dummy plot to add a second legend
    dummy_line = plt.Line2D([], [], color='none', label=custom_legend)
    second_legend = ax.legend(handles=[dummy_line], loc='upper left')

    # Add the first legend back to the plot
    ax.add_artist(first_legend)

    # Add grid
    ax.grid(True, alpha=0.5)

    # Show the plot
    plt.show()


format_data()
simulate_trades()
plot_graphs()
