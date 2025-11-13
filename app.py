from flask import Flask, request, jsonify
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# Temporary memory for active sessions
user_sessions = {}

# --- Google Sheets connection ---
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        raise Exception("❌ GOOGLE_SHEETS_CREDENTIALS environment variable not set on Render.")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("travel-bot-data").sheet1
    return sheet


# --- Helper function to clean values ---
def clean(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif value is None:
        return ""
    else:
        return str(value)


# --- Smart travel date extractor ---
def get_travel_dates(params, query_text):
    date_period = params.get('date-period')
    if date_period:
        start_date = date_period.get('startDate')
        end_date = date_period.get('endDate')
        return f"{start_date} → {end_date}"

    query_text = query_text.lower()
    current_year = datetime.now().year
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    selected_month = None
    for month_name, month_num in months.items():
        if month_name in query_text:
            selected_month = month_num
            break

    if selected_month:
        year = current_year + 1 if "next year" in query_text else current_year
        return f"{year}-{selected_month}-01 → {year}-{selected_month}-31"
    
    return "Unclear date"


# --- Webhook ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    intent_name = data['queryResult']['intent']['displayName']
    params = data['queryResult']['parameters']
    query_text = data['queryResult'].get('queryText', '')
    session = data['session']

    # Get user session
    if session not in user_sessions:
        user_sessions[session] = {}

    user_data = user_sessions[session]

    # --- DESTINATION INTENT ---
    if "destination" in intent_name.lower():
        city = params.get('city')
        country = params.get('country')
        destination = f"{city}, {country}" if city and country else city or country
        user_data["destination"] = clean(destination)
        return jsonify({
            'fulfillmentText': f"Got it! You're planning a trip to {destination}. When would you like to travel?"
        })

    # --- DATE INTENT ---
    elif "date" in intent_name.lower():
        travel_date = get_travel_dates(params, query_text)
        user_data["travel_date"] = clean(travel_date)
        return jsonify({
            'fulfillmentText': f"Perfect! When you travel on {travel_date}. How many people will be going?"
        })

    # --- PAX INTENT ---
    elif "pax" in intent_name.lower():
        pax = params.get('pax')
        if isinstance(pax, list):
            pax = pax[0] if pax else ""
        elif isinstance(pax, dict):
            pax = pax.get('amount', '')
        user_data["pax"] = clean(pax)
        return jsonify({
            'fulfillmentText': f"Great! Noted {pax} travelers. Can I have your name, email, and phone number?"
        })

    # --- CONTACT DETAILS INTENT ---
    elif "contact" in intent_name.lower():
        user_data["name"] = clean(params.get('name'))
        user_data["email"] = clean(params.get('email'))
        user_data["phone"] = clean(params.get('phone'))

        # Save to Google Sheet
        sheet = get_gsheet()
        sheet.append_row([
            user_data.get("name", ""),
            user_data.get("destination", ""),
            user_data.get("travel_date", ""),
            user_data.get("pax", ""),
            user_data.get("email", ""),
            user_data.get("phone", "")
        ])

        # clear session memory
        user_sessions.pop(session, None)

        return jsonify({
            'fulfillmentText': f"Thanks {user_data.get('name')}! Your trip to {user_data.get('destination')} on {user_data.get('travel_date')} for {user_data.get('pax')} people has been recorded. We'll contact you soon."
        })

    # --- DEFAULT ---
    return jsonify({'fulfillmentText': "I'm not sure what details to save. Could you please repeat?"})


@app.route('/')
def home():
    return "✅ Travel Bot Backend connected with Google Sheets and memory tracking!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
