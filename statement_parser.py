import pandas as pd
import io
import re
import pdfplumber

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
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2: continue
                        # Check if this table looks like an investment holdings table
                        header = [str(c).lower().replace('\n', ' ') for c in table[0] if c]
                        if any('quantity' in h for h in header) and any('value' in h for h in header):
                            # It's a relevant table
                            # Create a mapping for this table
                            col_names = [str(c).replace('\n', ' ') for c in table[0]]
                            for row in table[1:]:
                                if not row or len(row) != len(col_names): continue
                                row_dict = dict(zip(col_names, row))
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
            'symbol': next((c for c in df.columns if 'symbol' in str(c).lower() or 'scrip' in str(c).lower() or 'name' in str(c).lower()), None),
            'quantity': next((c for c in df.columns if 'qty' in str(c).lower() or 'quantity' in str(c).lower()), None),
            'avg_price': next((c for c in df.columns if 'avg' in str(c).lower() and 'price' in str(c).lower()), None),
            'total_cost': next((c for c in df.columns if 'cost' in str(c).lower() and 'value' in str(c).lower()), None),
            'cmp': next((c for c in df.columns if 'cmp' in str(c).lower() or 'current' in str(c).lower()), None),
            'category': next((c for c in df.columns if 'type' in str(c).lower() or 'category' in str(c).lower() or 'asset' in str(c).lower()), None)
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
                "platform": platform,
                "amount": round(qty * avg_price, 2), # Total investment
                "units": round(qty, 4),
                "avg_buy_price": round(avg_price, 2),
                "current_value": round(qty * curr_val, 2) if col_mapping['cmp'] and not ('value' in str(col_mapping['cmp']).lower() and 'current' in str(col_mapping['cmp']).lower()) else curr_val,
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
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))

        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(how='all')

        parsed_data = []
        col_mapping = {
            'symbol': next((c for c in df.columns if 'scheme' in str(c).lower() or 'instrument' in str(c).lower() or 'particular' in str(c).lower()), None),
            'quantity': next((c for c in df.columns if 'balance' in str(c).lower() or 'units' in str(c).lower() or 'qty' in str(c).lower()), None),
            'avg_price': next((c for c in df.columns if 'average' in str(c).lower() or 'cost' in str(c).lower()), None),
            'current_value': next((c for c in df.columns if 'market value' in str(c).lower() or 'current value' in str(c).lower()), None),
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

def identify_and_parse_statement(file_bytes, filename):
    """
    Attempts to identify the statement type and route to the correct parser.
    """
    filename_lower = filename.lower()
    
    if 'icici' in filename_lower or 'idirect' in filename_lower:
        return parse_icici_statement(file_bytes, filename)
    elif 'rathi' in filename_lower or 'anand' in filename_lower:
        return parse_anand_rathi_statement(file_bytes, filename)
    else:
        # Generic fallback: try ICICI parser heuristics as a best effort
        try:
            return parse_icici_statement(file_bytes, filename)
        except:
            return parse_anand_rathi_statement(file_bytes, filename)
