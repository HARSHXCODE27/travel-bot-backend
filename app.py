# from flask import Flask, request, jsonify
# import psycopg2
# import os

# app = Flask(__name__)

# # --- Database connection ---
# def get_db_connection():
#     return psycopg2.connect(
#         host=os.getenv("DB_HOST"),
#         database=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD")
#     )

# # --- Webhook route for Dialogflow ---
# @app.route('/webhook', methods=['POST'])
# def webhook():
#     data = request.get_json()
#     params = data['queryResult']['parameters']

#     destination = params.get('destination')
#     travel_date = params.get('travel_date')
#     pax = params.get('pax')
#     contact = params.get('contact')

#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute("""
#         INSERT INTO travel_inquiries (destination, travel_date, pax, contact)
#         VALUES (%s, %s, %s, %s)
#     """, (destination, travel_date, pax, contact))
#     conn.commit()
#     cur.close()
#     conn.close()

#     return jsonify({'fulfillmentText': f"Got it! Trip to {destination} saved. We'll contact you soon."})

# # --- Home route ---
# @app.route('/')
# def home():
#     return "Travel Bot Backend is running!"

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
    # Load credentials from environment variable (already stored in Render)
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    creds_dict = json.loads(creds_json)

    # Authenticate using service account
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)

    # Replace with the exact name of your Google Sheet
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

    # Connect to the Google Sheet
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
