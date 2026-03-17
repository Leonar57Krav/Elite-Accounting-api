from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime
import re
import pdfplumber

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

def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# ====================== SIMPLIFIED REPORT ======================
def create_simple_report(client_name, df, total_deductible):
    income = df[df['amount'] > 0]['amount'].sum()
    expenses = abs(df[df['amount'] < 0]['amount'].sum())
    breakdown = df.groupby('category')['amount'].sum().abs().to_dict()
    top_category = max(breakdown, key=breakdown.get) if breakdown else "none"
    
    html = f"""
    <html><body style="font-family: Arial; line-height: 1.6; max-width: 600px;">
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
        <p><strong>Quick Tip:</strong> Your biggest savings came from <strong>{top_category}</strong>.</p>
        <p>Reply <strong>APPROVE</strong> to file with IRS or tell me changes.</p>
        <p>— Elite Accounting USA</p>
    </body></html>
    """
    return html

# ====================== MAIN ENDPOINT (now accepts PDF files) ======================
@app.route('/agent', methods=['POST'])
def run_pdf_agent():
    client_name = request.form.get("client_name", "Valued Client")
    source = request.form.get("source", "gmail")
    
    # Support both text and PDF upload
    if 'pdf' in request.files:
        pdf_file = request.files['pdf']
        message_text = extract_text_from_pdf(pdf_file)
    else:
        message_text = request.form.get("message_body", "")
    
    # Simple extraction from the text
    transactions = []
    for line in message_text.split('\n'):
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([^\d$]+?)\s+([-$]?\d{1,3}(?:,\d{3})*\.\d{2})', line)
        if match:
            amount = float(re.sub(r'[^\d.-]', '', match.group(3)).replace(',', '.'))
            transactions.append({
                "date": match.group(1).replace('/', '-'),
                "description": match.group(2).strip(),
                "amount": amount
            })
    
    if not transactions:
        return jsonify({"status": "error", "message": "Could not read the PDF or text. Try a clearer bank statement."}), 400
    
    df = pd.DataFrame(transactions)
    df = SimpleCategorizer().auto_categorize(df)
    
    total_deductible = abs(df[df['category'].isin(["office_supplies","software","travel","meals","marketing","home_office","vehicle"])]['amount'].sum())
    
    html_report = create_simple_report(client_name, df, total_deductible)
    
    return jsonify({
        "status": "success",
        "client": client_name,
        "total_deductible": round(total_deductible, 2),
        "html_report": html_report,
        "simple_summary": f"Tax savings: ${total_deductible:,.0f}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
