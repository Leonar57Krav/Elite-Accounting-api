from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime
import re
import pdfplumber
from io import BytesIO

app = Flask(__name__)

# Your existing rules (unchanged)
DEFAULT_RULES = {
    r"amazon|office depot|staples": "office_supplies",
    r"chatgpt|aws|zoom|adobe": "software",
    r"uber|lyft|delta": "travel",
    r"starbucks|doordash|restaurant": "meals",
    r"google ads|facebook": "marketing",
    r"home office|internet|phone": "home_office",
    r"gas|fuel|mileage": "vehicle",
}

def extract_transactions_from_text(text: str) -> list:
    transactions = []
    for line in text.split('\n'):
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([^\d$]+?)\s+([-$]?\d{1,3}(?:,\d{3})*\.\d{2})', line, re.IGNORECASE)
        if match:
            amount = float(re.sub(r'[^\d.-]', '', match.group(3)).replace(',', '.'))
            transactions.append({
                "date": match.group(1).replace('/', '-'),
                "description": match.group(2).strip(),
                "amount": amount
            })
    return transactions

@app.route('/agent', methods=['POST'])
def process_pdf():
    client_name = request.form.get("client_name", "Valued Client")

    if 'pdf' in request.files:
        file = request.files['pdf']
        pdf_bytes = BytesIO(file.read())
        text = ""
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    else:
        text = request.form.get("message_body", "")

    if not text:
        return jsonify({"status": "error", "message": "No text or PDF provided"}), 400

    transactions = extract_transactions_from_text(text)
    if not transactions:
        return jsonify({"status": "error", "message": "No transactions found in text/PDF"}), 400

    df = pd.DataFrame(transactions)
    df['category'] = df['description'].str.lower().apply(
        lambda desc: next((cat for regex, cat in DEFAULT_RULES.items() if re.search(regex, desc, re.IGNORECASE)), "other")
    )

    deductible_categories = ["office_supplies", "software", "travel", "meals", "marketing", "home_office", "vehicle"]
    total_deductible = abs(df[df['category'].isin(deductible_categories)]['amount'].sum())

    html_report = f"""
    <html>
    <body style="font-family: Arial; line-height: 1.6; max-width: 600px;">
        <h2>Elite Accounting USA — Simple Monthly Summary</h2>
        <p>Hi {client_name},</p>
        <p>Here's what we found in your bank statement:</p>
        <h3>💰 Quick Numbers</h3>
        <ul>
            <li><strong>Income:</strong> ${df[df['amount'] > 0]['amount'].sum():,.0f}</li>
            <li><strong>Expenses:</strong> ${abs(df[df['amount'] < 0]['amount'].sum()):,.0f}</li>
            <li><strong>Tax Savings Found:</strong> <span style="color:green; font-size:18px;"><strong>${total_deductible:,.0f}</strong></span></li>
        </ul>
        <p><strong>Quick Tip:</strong> Your biggest savings came from the top category above.</p>
        <p>Reply <strong>APPROVE</strong> to file with IRS or tell me changes.</p>
        <p>— Elite Accounting USA</p>
    </body>
    </html>
    """

    return jsonify({
        "status": "success",
        "client": client_name,
        "total_deductible": round(total_deductible, 2),
        "html_report": html_report
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
