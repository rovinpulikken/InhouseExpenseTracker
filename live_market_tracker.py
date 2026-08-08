import requests
import pandas as pd
import datetime
import random

def fetch_amfi_nav_data():
    """
    Fetches the latest NAV data for Mutual Funds from the AMFI API.
    Returns a dictionary mapping Scheme Name (lower) to NAV.
    """
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.split('\\n')
        
        nav_dict = {}
        for line in lines:
            parts = line.split(';')
            if len(parts) >= 5 and parts[0].isdigit():
                scheme_name = parts[3].strip().lower()
                nav_str = parts[4].strip()
                try:
                    nav_dict[scheme_name] = float(nav_str)
                except ValueError:
                    continue
        return nav_dict
    except Exception as e:
        print(f"Failed to fetch AMFI NAV data: {e}")
        return {}

def get_simulated_live_stock_prices(symbols, current_prices):
    """
    Since free live stock APIs (like Yahoo Finance) can be flaky or require API keys,
    we simulate a live 'tick' based on the last known price for demonstration purposes,
    with a small random variance (-2% to +2%).
    """
    updated_prices = {}
    for i, symbol in enumerate(symbols):
        base_price = current_prices[i] if current_prices[i] > 0 else 100.0
        # Simulate a small market movement
        movement_percent = random.uniform(-0.02, 0.02)
        new_price = round(base_price * (1 + movement_percent), 2)
        updated_prices[symbol] = new_price
    return updated_prices

def update_portfolio_live_prices(portfolio_df):
    """
    Takes a dataframe of investments and attempts to update current prices and values.
    Returns the updated dataframe.
    """
    if portfolio_df.empty:
        return portfolio_df

    # 1. Update Mutual Funds
    mf_mask = portfolio_df['type'].str.lower().str.contains('mutual fund', na=False)
    if mf_mask.any():
        amfi_data = fetch_amfi_nav_data()
        if amfi_data:
            for idx, row in portfolio_df[mf_mask].iterrows():
                # Try exact match, or partial match
                scheme_name = str(row.get('description', '')).lower()
                if not scheme_name:
                    continue
                    
                match = amfi_data.get(scheme_name)
                # Fallback: substring search (can be slow but usually fine for small portfolios)
                if not match:
                    for amfi_name, nav in amfi_data.items():
                        if scheme_name in amfi_name or amfi_name in scheme_name:
                            match = nav
                            break
                
                if match and row.get('units', 0) > 0:
                    portfolio_df.at[idx, 'current_value'] = round(row['units'] * match, 2)
                    portfolio_df.at[idx, 'last_updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 2. Update Stocks (Equity)
    eq_mask = portfolio_df['type'].str.lower() == 'equity'
    if eq_mask.any():
        eq_symbols = portfolio_df.loc[eq_mask, 'description'].tolist()
        
        # Calculate derived price from current value / units if we don't have price explicitly stored in this df version
        current_derived_prices = []
        for _, row in portfolio_df[eq_mask].iterrows():
            units = row.get('units', 0)
            if units > 0:
                current_derived_prices.append(row.get('current_value', 0) / units)
            else:
                current_derived_prices.append(0)
                
        new_prices = get_simulated_live_stock_prices(eq_symbols, current_derived_prices)
        
        for idx, row in portfolio_df[eq_mask].iterrows():
            symbol = row['description']
            units = row.get('units', 0)
            if symbol in new_prices and units > 0:
                portfolio_df.at[idx, 'current_value'] = round(units * new_prices[symbol], 2)
                portfolio_df.at[idx, 'last_updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return portfolio_df
