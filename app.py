# from flask import Flask, request, jsonify
# import gspread
# import os
# import json
# from google.oauth2.service_account import Credentials

# app = Flask(__name__)

# # --- Google Sheets connection ---
# def get_gsheet():
#     # Load credentials from environment variable (already stored in Render)
#     creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
#     creds_dict = json.loads(creds_json)

#     # Authenticate using service account
#     creds = Credentials.from_service_account_info(
#         creds_dict,
#         scopes=["https://www.googleapis.com/auth/spreadsheets"]
#     )

#     client = gspread.authorize(creds)

#     # Replace with the exact name of your Google Sheet
#     sheet = client.open("travel-bot-data").sheet1
#     return sheet


# # --- Webhook route for Dialogflow ---
# @app.route('/webhook', methods=['POST'])
# def webhook():
#     data = request.get_json()
#     params = data['queryResult']['parameters']

#     # Get parameters sent by Dialogflow
#     name = params.get('name')
#     destination = params.get('destination')
#     travel_date = params.get('date')
#     pax = params.get('pax')
#     email = params.get('email')
#     phone = params.get('phone')

#     # Connect to the Google Sheet
#     sheet = get_gsheet()

#     # Append a new row
#     sheet.append_row([name, destination, travel_date, pax, email, phone])

#     # Respond back to Dialogflow
#     return jsonify({
#         'fulfillmentText': f"Thanks {name}! Your trip to {destination} on {travel_date} for {pax} people has been recorded. We'll contact you soon."
#     })


# # --- Health check route ---
# @app.route('/')
# def home():
#     return "✅ Travel Bot Backend connected to Google Sheets!"

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=10000)

from flask import Flask, request, jsonify
import gspread
import os
import json
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- Google Sheets connection ---
def get_gsheet():
    creds = None

    # 1️⃣ Try loading credentials from environment variable (Render)
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            print("✅ Loaded credentials from environment variable.")
        except Exception as e:
            print("⚠️ Failed to load credentials from environment variable:", e)

    # 2️⃣ If no env var found, fall back to local JSON file (for local testing)
    if not creds:
        try:
            creds = Credentials.from_service_account_file(
                "travel-bot-botshyka-81a67d5ce0c5.json",
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            print("✅ Loaded credentials from local JSON file.")
        except FileNotFoundError:
            raise Exception("❌ No credentials found. Please set GOOGLE_SHEETS_CREDENTIALS env var or keep local JSON file.")

    # 3️⃣ Authorize Google Sheets client
    client = gspread.authorize(creds)

    # Replace with your actual Sheet name
    sheet = client.open("travel-bot-data").sheet1
    return sheet


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
