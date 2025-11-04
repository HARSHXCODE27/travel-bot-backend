from flask import Flask, request, jsonify
import gspread
import os
import json
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- Google Sheets connection ---
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if not creds_json:
        raise Exception("❌ GOOGLE_SHEETS_CREDENTIALS environment variable not set on Render.")

    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        print("✅ Successfully authorized with Google Sheets via environment variable.")
        sheet = client.open("travel-bot-data").sheet1
        return sheet
    except Exception as e:
        print("❌ Failed to authorize Google Sheets:", str(e))
        raise


# --- Test route to verify environment variable ---
@app.route("/test-env")
def test_env():
    if os.getenv("GOOGLE_SHEETS_CREDENTIALS"):
        return "✅ Environment variable found"
    else:
        return "❌ Not found"


# --- Webhook route for Dialogflow ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    params = data['queryResult']['parameters']

    # Get parameters sent by Dialogflow
    name = params.get('name')
    destination = params.get('destination')
    travel_date = params.get('date')
    pax = params.get('pax')
    email = params.get('email')
    phone = params.get('phone')

    # Connect to Google Sheet
    sheet = get_gsheet()

    # Append a new row
    sheet.append_row([name, destination, travel_date, pax, email, phone])

    # Respond back to Dialogflow
    return jsonify({
        'fulfillmentText': f"Thanks {name}! Your trip to {destination} on {travel_date} for {pax} people has been recorded. We'll contact you soon."
    })


# --- Health check route ---
@app.route('/')
def home():
    return "✅ Travel Bot Backend connected to Google Sheets!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
