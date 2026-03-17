from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime
import re

app = Flask(__name__)

# ====================== CONFIG & CONSTANTS (USA focus) ======================
DEDUCTIBLE_CATEGORIES = {
    "office_supplies", "software", "travel", "meals_entertainment",  # 50% rule auto-noted
    "marketing", "professional_fees", "home_office", "vehicle_mileage",
    "training", "bank_charges", "depreciation", "internet_phone"
}

DEFAULT_RULES = {
    r"amazon|office depot|staples": "office_supplies",
    r"chatgpt|aws|zoom|adobe|canva": "software",
    r"uber|lyft|delta|american airlines": "travel",
    r"starbucks|doordash|restaurant": "meals_entertainment",
    r"google ads|facebook ads|linkedin": "marketing",
    r"attorney|accountant|consultant": "professional_fees",
    r"home office|internet|phone": "home_office",
    r"gas|fuel|car service|mileage": "vehicle_mileage",
}

# ====================== CORE CLASSES ======================
class TransactionCategorizer:
    def __init__(self):
        self.rules = DEFAULT_RULES.copy()

    def auto_categorize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['category'] = df['description'].str.lower().apply(self._match_rule)
        return df

    def _match_rule(self, description: str) -> str:
        if not description:
            return "uncategorized"
        for regex, category in self.rules.items():
            if re.search(regex, description, re.IGNORECASE):
                return category
        return "uncategorized"

class TaxManager:
    def __init__(self):
        self.deductible_categories = DEDUCTIBLE_CATEGORIES.copy()

    def mark_deductibles(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['deductible'] = df['category'].isin(self.deductible_categories)
        df['irs_note'] = df.apply(lambda row: "50% meals limit applies" if row['category'] == "meals_entertainment" and row['deductible'] else "", axis=1)
        return df

    def generate_tax_report(self, df: pd.DataFrame, tax_year: int) -> dict:
        deductible = df[df['deductible'] == True]
        report = {
            "tax_year": tax_year,
            "total_income": float(df[df['amount'] > 0]['amount'].sum()),
            "total_expenses": float(abs(df[df['amount'] < 0]['amount'].sum())),
            "total_deductible": float(abs(deductible['amount'].sum())),
            "deductible_breakdown": deductible.groupby('category')['amount'].sum().abs().to_dict(),
            "irs_ready": "TurboTax / IRS e-file export ready",
            "export_date": datetime.now().isoformat()
        }
        return report

class ProfitabilityTracker:
    def calculate_profitability(self, df: pd.DataFrame) -> pd.DataFrame:
        summary = df.groupby('category').agg({
            'amount': ['sum', 'count']
        }).reset_index()
        summary.columns = ['category', 'total', 'transactions']
        summary['margin_note'] = "Review for profitability"
        return summary

# ====================== EMAIL / WHATSAPP EXTRACTION ======================
def extract_transactions_from_message(message_text: str) -> list:
    transactions = []
    date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})'
    amount_pattern = r'[-$]?[\d,]+\.?\d{2}'
    
    lines = message_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        date_match = re.search(date_pattern, line)
        amount_match = re.search(amount_pattern, line)
        
        if date_match and amount_match:
            date_str = date_match.group(1).replace('/', '-')
            amount_str = re.sub(r'[^\d.-]', '', amount_match.group(0)).replace(',', '.')
            try:
                amount = float(amount_str)
            except:
                continue
            
            desc = re.sub(r'[\d/$-]', '', line).strip()[:100] or "Bank transaction"
            transactions.append({
                "date": date_str[:10],
                "description": desc,
                "amount": amount
            })
    return transactions

# ====================== MAIN AI AGENT ENDPOINT ======================
@app.route('/agent', methods=['POST'])
def run_elite_usa_agent():
    data = request.get_json()
    client_name = data.get("client_name", "Valued Client")
    message_body = data.get("message_body", "")
    source = data.get("source", "gmail")
    
    transactions = extract_transactions_from_message(message_body)
    
    if not transactions:
        return jsonify({"status": "error", "message": "No transactions extracted. Forward a clearer statement."}), 400
    
    df = pd.DataFrame(transactions)
    df = TransactionCategorizer().auto_categorize(df)
    df = TaxManager().mark_deductibles(df)
    
    tax_report = TaxManager().generate_tax_report(df, datetime.now().year)
    profitability = ProfitabilityTracker().calculate_profitability(df)
    
    html_report = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a73e8;">Elite Accounting USA – Monthly Report</h2>
        <p>Dear {client_name},</p>
        <p>Processed from your {source.upper()} ({len(transactions)} transactions).</p>
        <h3>✅ IRS Deductions Found: ${abs(tax_report['total_deductible']):,.2f}</h3>
        <h3>📊 Profitability Snapshot</h3>
        {profitability.to_html(index=False)}
        <p>Reply <strong>APPROVE</strong> to file or tell me changes.</p>
        <p>Elite Accounting • U.S.A.</p>
    </body></html>
    """
    
    return jsonify({
        "status": "success",
        "client": client_name,
        "email_subject": f"Elite Accounting Report – {client_name} – {datetime.now().strftime('%B %Y')}",
        "html_report": html_report,
        "total_deductible": float(abs(tax_report['total_deductible'])),
        "extracted_count": len(transactions)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
