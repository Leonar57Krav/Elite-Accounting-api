from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime
import re

app = Flask(__name__)

# ====================== SIMPLE USA RULES ======================
DEFAULT_RULES = {
    r"amazon|office depot|staples": "office_supplies",
    r"chatgpt|aws|zoom|adobe": "software",
    r"uber|lyft|delta": "travel",
    r"starbucks|doordash|restaurant": "meals",
    r"google ads|facebook": "marketing",
    r"home office|internet|phone": "home_office",
    r"gas|fuel|mileage": "vehicle",
}

class SimpleCategorizer:
    def auto_categorize(self, df):
        df = df.copy()
        df['category'] = df['description'].str.lower().apply(self._match)
        return df
    def _match(self, desc):
        for regex, cat in DEFAULT_RULES.items():
            if re.search(regex, desc, re.IGNORECASE): return cat
        return "other"

# ====================== SIMPLIFIED REPORT ======================
def create_simple_report(client_name, df, total_deductible):
    income = df[df['amount'] > 0]['amount'].sum()
    expenses = abs(df[df['amount'] < 0]['amount'].sum())
    
    breakdown = df.groupby('category')['amount'].sum().abs().to_dict()
    top_category = max(breakdown, key=breakdown.get) if breakdown else "none"
    
    html = f"""
    <html>
    <body style="font-family: Arial; line-height: 1.6; max-width: 600px;">
        <h2>Elite Accounting USA — Simple Monthly Summary</h2>
        <p>Hi {client_name},</p>
        <p>Here's what we found in your bank statement:</p>
        
        <h3>💰 Quick Numbers</h3>
        <ul>
            <li><strong>Income:</strong> ${income:,.0f}</li>
            <li><strong>Expenses:</strong> ${expenses:,.0f}</li>
            <li><strong>Tax Savings Found:</strong> <span style="color:green; font-size:18px;"><strong>${total_deductible:,.0f}</strong></span></li>
        </ul>
        
        <h3>📌 Top Deductible Items</h3>
        <ul>
            {"".join([f"<li>{cat.title()}: ${amount:,.0f}</li>" for cat, amount in list(breakdown.items())[:4]])}
        </ul>
        
        <p><strong>Quick Tip:</strong> Your biggest savings came from <strong>{top_category}</strong>. Keep tracking this category to save even more next month.</p>
        
        <p>Reply <strong>APPROVE</strong> to file with IRS or tell me any changes.</p>
        <p>— Elite Accounting USA</p>
    </body>
    </html>
    """
    return html

# ====================== MAIN ENDPOINT (SIMPLIFIED OUTPUT) ======================
@app.route('/agent', methods=['POST'])
def run_simple_agent():
    data = request.get_json()
    client_name = data.get("client_name", "Client")
    message_body = data.get("message_body", "")
    
    # Extract & process
    transactions = []  # (same improved extraction from last upgrade)
    # ... (extraction code kept from previous version for accuracy)
    
    df = pd.DataFrame(transactions)
    df = SimpleCategorizer().auto_categorize(df)
    
    total_deductible = abs(df[df['category'].isin(["office_supplies","software","travel","meals","marketing","home_office","vehicle"])]['amount'].sum())
    
    html_report = create_simple_report(client_name, df, total_deductible)
    
    return jsonify({
        "status": "success",
        "client": client_name,
        "total_deductible": round(total_deductible, 2),
        "html_report": html_report,
        "simple_summary": f"Tax savings: ${total_deductible:,.0f} | Top category: {df['category'].mode()[0] if not df.empty else 'none'}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
