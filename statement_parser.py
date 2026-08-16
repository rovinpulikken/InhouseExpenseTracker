import pandas as pd
import io
import re
import pdfplumber
import mimetypes
import json
import datetime

def parse_icici_statement(file_bytes, filename):
    """
    Parses ICICI Direct Portfolio Statement (CSV, Excel, or PDF).
    Expected columns might include: 'Stock Symbol', 'Quantity', 'Average Price', 'Current Market Price', 'Value'
    Returns a list of dictionaries with standard keys.
    """
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(file_bytes))
        elif filename.lower().endswith('.pdf'):
            # Parse PDF using pdfplumber
            all_rows = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                last_col_names = None
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2: continue
                        
                        # Check if this table looks like an investment holdings table
                        header = [str(c).lower().replace('\n', ' ') for c in table[0] if c]
                        
                        # If the table starts with recognized headers, grab them
                        if any('quantity' in h for h in header) and any('value' in h for h in header):
                            last_col_names = [str(c).replace('\n', ' ') for c in table[0]]
                            start_idx = 1
                        elif last_col_names:
                            # It's a continuation table on the next page
                            start_idx = 0
                        else:
                            continue
                            
                        for row in table[start_idx:]:
                            if not row or len(row) != len(last_col_names): continue
                            row_dict = dict(zip(last_col_names, row))
                            all_rows.append(row_dict)
            if not all_rows:
                return []
            df = pd.DataFrame(all_rows)
        else:
            raise Exception("Unsupported file format.")

        # Basic cleanup: remove unnamed columns and completely empty rows
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(how='all')
        
        parsed_data = []
        # Fallback heuristic if columns are completely unexpected
        col_mapping = {
            'symbol': next((c for c in df.columns if any(x in str(c).lower() for x in ['stock code', 'name', 'symbol', 'scheme', 'instrument', 'particular'])), None),
            'quantity': next((c for c in df.columns if any(x in str(c).lower() for x in ['quantity', 'qty', 'unit', 'balance'])), None),
            'avg_price': next((c for c in df.columns if any(x in str(c).lower() for x in ['average', 'avg price', 'cost'])), None),
            'total_cost': next((c for c in df.columns if 'total' in str(c).lower() and 'cost' in str(c).lower()), None),
            'cmp': next((c for c in df.columns if any(x in str(c).lower() for x in ['current value', 'cmp', 'market value'])), None),
            'category': next((c for c in df.columns if any(x in str(c).lower() for x in ['asset class', 'category', 'type'])), None),
            'platform': next((c for c in df.columns if any(x in str(c).lower() for x in ['platform', 'broker'])), None),
            'investment_amount': next((c for c in df.columns if any(x in str(c).lower() for x in ['invested amount', 'investment amount', 'amount'])), None),
            'year_invested': next((c for c in df.columns if any(x in str(c).lower() for x in ['year'])), None),
            'market_cap': next((c for c in df.columns if any(x in str(c).lower() for x in ['market cap'])), None),
            'sector_segment': next((c for c in df.columns if any(x in str(c).lower() for x in ['sector', 'theme'])), None)
        }

        for _, row in df.iterrows():
            # Skip rows where symbol or quantity is essentially null
            if not col_mapping['symbol'] or not col_mapping['quantity']: continue
            
            symbol_val = row.get(col_mapping['symbol'])
            if pd.isna(symbol_val): continue

            # Clean and parse quantity and price
            qty_val = str(row.get(col_mapping['quantity'], 0)).replace(',', '')
            avg_price_val = str(row.get(col_mapping['avg_price'], 0)).replace(',', '')
            total_cost_val = str(row.get(col_mapping['total_cost'], 0)).replace(',', '')
            cmp_val = str(row.get(col_mapping['cmp'], 0)).replace(',', '')
            
            try:
                qty = float(qty_val) if qty_val.strip() else 0.0
                curr_val = float(cmp_val) if cmp_val.strip() else 0.0
                
                avg_price = 0.0
                if col_mapping['avg_price']:
                    avg_price = float(avg_price_val) if avg_price_val.strip() else 0.0
                elif col_mapping['total_cost']:
                    tc = float(total_cost_val) if total_cost_val.strip() else 0.0
                    avg_price = (tc / qty) if qty > 0 else 0.0
                    
            except ValueError:
                continue

            # Skip header repeats or invalid rows
            if qty <= 0: continue

            # Determine Platform and Type
            platform = "ICICI Direct"
            asset_type = "Equity" # Default
            if col_mapping['category'] and not pd.isna(row.get(col_mapping['category'])):
                cat_val = str(row.get(col_mapping['category'])).lower()
                if 'mutual fund' in cat_val or 'mf' in cat_val:
                    asset_type = "Mutual Funds"
                elif 'bond' in cat_val or 'deposit' in cat_val or 'fd' in cat_val:
                    asset_type = "Deposits"
            
            # Simple fallback detection based on symbol name
            elif 'mf' in str(symbol_val).lower() or 'fund' in str(symbol_val).lower():
                asset_type = "Mutual Funds"

            parsed_data.append({
                "type": asset_type,
                "platform": str(row.get(col_mapping['platform'], platform)).strip() if col_mapping.get('platform') and pd.notna(row.get(col_mapping['platform'])) else platform,
                "amount": float(str(row.get(col_mapping['investment_amount'], 0)).replace(',','')) if col_mapping.get('investment_amount') and pd.notna(row.get(col_mapping['investment_amount'])) else round(qty * avg_price, 2),
                "year_invested": int(row.get(col_mapping['year_invested'], datetime.datetime.now().year)) if col_mapping.get('year_invested') and pd.notna(row.get(col_mapping['year_invested'])) else datetime.datetime.now().year,
                "units": round(qty, 4),
                "avg_buy_price": round(avg_price, 2),
                "current_value": round(qty * curr_val, 2) if col_mapping['cmp'] and not ('value' in str(col_mapping['cmp']).lower() and 'current' in str(col_mapping['cmp']).lower()) else curr_val,
                "market_cap": str(row.get(col_mapping['market_cap'], "Unknown")).strip() if col_mapping.get('market_cap') and pd.notna(row.get(col_mapping['market_cap'])) else "Unknown",
                "sector_segment": str(row.get(col_mapping['sector_segment'], "Unknown")).strip() if col_mapping.get('sector_segment') and pd.notna(row.get(col_mapping['sector_segment'])) else "Unknown",
                "name_or_symbol": str(symbol_val).strip()
            })

        return parsed_data
    except Exception as e:
        raise Exception(f"Failed to parse ICICI statement: {str(e)}")


def parse_anand_rathi_statement(file_bytes, filename):
    """
    Parses Anand Rathi Wealth Statement (CSV or Excel).
    Similar heuristic extraction as ICICI, adjusted for typical Anand Rathi column names.
    """
    try:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(file_bytes))
        elif filename.lower().endswith('.pdf'):
            all_rows = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                last_col_names = None
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2: continue
                        
                        # Grab headers from the very first table we encounter
                        if not last_col_names:
                            last_col_names = [str(c).replace('\n', ' ') for c in table[0]]
                            start_idx = 1
                        else:
                            # Check if this table repeats the headers
                            current_headers = [str(c).replace('\n', ' ') for c in table[0]]
                            if current_headers == last_col_names:
                                start_idx = 1
                            else:
                                start_idx = 0
                                
                        for row in table[start_idx:]:
                            if not row or len(row) != len(last_col_names): continue
                            all_rows.append(dict(zip(last_col_names, row)))
            if not all_rows:
                return []
            df = pd.DataFrame(all_rows)
        else:
            raise Exception("Unsupported file format.")

        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(how='all')

        parsed_data = []
        col_mapping = {
            'symbol': next((c for c in df.columns if any(x in str(c).lower() for x in ['stock code', 'name', 'symbol', 'scheme', 'instrument', 'particular'])), None),
            'quantity': next((c for c in df.columns if any(x in str(c).lower() for x in ['quantity', 'qty', 'unit', 'balance'])), None),
            'avg_price': next((c for c in df.columns if any(x in str(c).lower() for x in ['average', 'avg price', 'cost'])), None),
            'current_value': next((c for c in df.columns if any(x in str(c).lower() for x in ['current value', 'cmp', 'market value'])), None),
        }
        
        # If headers are missing, default to some standard if possible, else return empty
        if not col_mapping['symbol'] or not col_mapping['quantity']:
             return []

        for _, row in df.iterrows():
            symbol_val = row.get(col_mapping['symbol'])
            if pd.isna(symbol_val): continue

            qty_val = str(row.get(col_mapping['quantity'], 0)).replace(',', '')
            avg_price_val = str(row.get(col_mapping['avg_price'], 0)).replace(',', '')
            curr_val_str = str(row.get(col_mapping['current_value'], 0)).replace(',', '')

            try:
                qty = float(qty_val) if qty_val.strip() else 0.0
                avg_price = float(avg_price_val) if avg_price_val.strip() else 0.0
                curr_val = float(curr_val_str) if curr_val_str.strip() else 0.0
            except ValueError:
                continue

            if qty <= 0: continue

            platform = "Anand Rathi"
            asset_type = "Mutual Funds" # Often MF heavy, adjust based on name
            
            if 'equity' in str(symbol_val).lower():
                asset_type = "Equity"

            parsed_data.append({
                "type": asset_type,
                "platform": platform,
                "amount": round(qty * avg_price, 2) if avg_price > 0 else round(curr_val * 0.9, 2), # Fallback estimate
                "units": round(qty, 4),
                "avg_buy_price": round(avg_price, 2) if avg_price > 0 else 0.0,
                "current_value": round(curr_val, 2),
                "name_or_symbol": str(symbol_val).strip()
            })

        return parsed_data
    except Exception as e:
        raise Exception(f"Failed to parse Anand Rathi statement: {str(e)}")

def parse_investment_with_gemini(file_bytes, filename, api_key):
    """
    Parses any investment statement using Gemini 2.5 Flash via google-genai SDK.
    """
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key)
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        if filename.lower().endswith('.csv'):
            mime_type = 'text/csv'
        elif filename.lower().endswith('.pdf'):
            mime_type = 'application/pdf'
        elif filename.lower().endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xls'):
            mime_type = 'application/vnd.ms-excel'
        else:
            mime_type = 'application/octet-stream'

    system_prompt = """
You are an expert financial AI assistant. Your task is to extract investment holdings from the provided broker statement or portfolio document.
The document may be an image, PDF, CSV, or Excel file. Extract the data into a strict JSON list of dictionaries.

Each dictionary MUST have the following keys and data types:
- "name_or_symbol": (string) The name of the stock, mutual fund, or asset.
- "type": (string) The asset type (e.g., "Equity", "Mutual Funds", "Deposits", "Alternative Asset").
- "platform": (string) The broker or platform name (e.g., "ICICI Direct", "Zerodha", "Anand Rathi", etc.). Try to infer from the document context. If unknown, use "Generic Broker".
- "amount": (float) The total invested amount or cost.
- "units": (float) The total quantity or units held.
- "avg_buy_price": (float) The average purchase price.
- "current_value": (float) The TOTAL current market value of the holding. IMPORTANT: This MUST be the total value (i.e. units multiplied by current market price). If the document only provides a Current Market Price (CMP) per unit, you MUST multiply it by the number of units to get this total value. Do NOT put the unit price here.

Rules:
1. Return ONLY the JSON array. Do not include markdown codeblocks (like ```json), explanations, or text outside the JSON.
2. If any numeric value is missing, use 0.0.
3. Clean all numbers (remove commas, currency symbols).

Example Output:
[
  {
    "name_or_symbol": "HDFC Bank Ltd",
    "type": "Equity",
    "platform": "Zerodha",
    "amount": 50000.0,
    "units": 30.5,
    "avg_buy_price": 1639.34,
    "current_value": 52000.0
  }
]
"""

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            system_prompt
        ]
    )
    
    raw_text = response.text.strip()
    if "```" in raw_text:
        raw_text = re.sub(r"```json\s*", "", raw_text)
        raw_text = re.sub(r"```\s*", "", raw_text)
        
    parsed_json = json.loads(raw_text.strip())
    if not isinstance(parsed_json, list):
        raise ValueError("Gemini did not return a valid JSON list.")
    
    return parsed_json


def identify_and_parse_statement(file_bytes, filename, api_key=None):
    """
    Attempts to identify the statement type and route to the correct parser.
    Uses Gemini API if the key is provided, falling back to heuristics.
    """
    parsed_data = None
    if api_key:
        try:
            parsed_data = parse_investment_with_gemini(file_bytes, filename, api_key)
        except Exception as e:
            print(f"Gemini parsing failed: {e}. Falling back to heuristic parsers.")

    if not parsed_data:
        filename_lower = filename.lower()
        if 'icici' in filename_lower or 'idirect' in filename_lower:
            parsed_data = parse_icici_statement(file_bytes, filename)
        elif 'rathi' in filename_lower or 'anand' in filename_lower:
            parsed_data = parse_anand_rathi_statement(file_bytes, filename)
        else:
            # Generic fallback: try ICICI parser heuristics as a best effort
            try:
                parsed_data = parse_icici_statement(file_bytes, filename)
            except:
                parsed_data = parse_anand_rathi_statement(file_bytes, filename)

    # Post-processing: Programmatically verify and fix `current_value` calculation
    if parsed_data:
        for item in parsed_data:
            val = float(item.get("current_value", 0.0))
            avg_price = float(item.get("avg_buy_price", 0.0))
            units = float(item.get("units", 0.0))
            
            # If the current_value is suspiciously close to the unit average buy price (and units > 1),
            # the parser likely extracted the Current Market Price (per unit) instead of the total value.
            if val > 0 and units > 1 and avg_price > 0:
                # If val is within 100x of avg_price, but total investment is much larger, it's a unit price.
                if 0.05 * avg_price < val < 20.0 * avg_price: 
                    # It's highly likely to be the CMP per unit. Multiply by units to get total value.
                    item["current_value"] = round(val * units, 2)
                    
    return parsed_data
