import pandas as pd
from typing import Tuple, List, Dict
import copy

def simulate_debt_payoff(debts_df: pd.DataFrame, strategy: str, total_monthly_budget: float) -> Tuple[int, float, pd.DataFrame]:
    """
    Simulates debt payoff using Avalanche or Snowball method.
    Returns: (total_months, total_interest_paid, timeline_df)
    """
    # Create a deep copy of debts to simulate
    debts = []
    for _, row in debts_df.iterrows():
        if row['outstanding_principal'] > 0:
            debts.append({
                'id': row.get('id', 0),
                'name': row['debt_name'],
                'balance': float(row['outstanding_principal']),
                'apr': float(row['interest_rate_percent']),
                'emi': float(row['monthly_emi'])
            })
            
    # Sort debts based on strategy
    if strategy.startswith("Avalanche"):
        # Highest APR first
        debts.sort(key=lambda x: x['apr'], reverse=True)
    elif strategy.startswith("Snowball"):
        # Lowest balance first
        debts.sort(key=lambda x: x['balance'])
        
    total_months = 0
    total_interest_paid = 0.0
    timeline = []
    
    # Record month 0
    total_balance = sum(d['balance'] for d in debts)
    timeline.append({"Month": 0, "Total Balance": total_balance})
    
    while total_balance > 0.01 and total_months < 1200: # 100 years max to prevent infinite loops
        total_months += 1
        
        # 1. Accrue interest for all active debts
        for d in debts:
            if d['balance'] > 0:
                interest = d['balance'] * (d['apr'] / 100.0) / 12.0
                d['balance'] += interest
                total_interest_paid += interest
                
        # 2. Pay minimums and calculate extra cash
        remaining_budget = total_monthly_budget
        for d in debts:
            if d['balance'] > 0:
                # Minimum payment is either the EMI or the remaining balance if it's smaller
                min_payment = min(d['balance'], d['emi'])
                
                # If budget is lower than minimums, we still deduct minimum (assuming the user somehow pays it)
                # but it consumes budget
                payment = min(min_payment, remaining_budget)
                if payment > 0:
                    d['balance'] -= payment
                    remaining_budget -= payment
                else:
                    # Budget shortfall! The user can't even afford minimums.
                    # We still apply minimum payment for simulation purposes, but remaining budget goes negative (effectively 0 for extra cash)
                    d['balance'] -= min_payment
                    remaining_budget -= min_payment
                    
        # 3. Cascade Extra Cash (and freed up minimums)
        # remaining_budget is our P_extra
        if remaining_budget > 0:
            for d in debts:
                if d['balance'] > 0 and remaining_budget > 0:
                    payment = min(d['balance'], remaining_budget)
                    d['balance'] -= payment
                    remaining_budget -= payment
                    
        total_balance = sum(d['balance'] for d in debts)
        timeline.append({"Month": total_months, "Total Balance": total_balance})

    timeline_df = pd.DataFrame(timeline)
    return total_months, total_interest_paid, timeline_df
