from flask import Flask, request, jsonify
import os
import json
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

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
        raise Exception("❌ GOOGLE_SHEETS_CREDENTIALS env variable missing!")

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


# --- Month-Year Normalizer (ONLY THIS MATTERS NOW) ---
MONTHS = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

def normalize_month_year(text):
    text = text.lower().strip()
    current_year = datetime.now().year

    # 1) Month name + year
    for name, num in MONTHS.items():
        if name in text:
            year_match = re.search(r"(20\d{2}|\d{2})", text)
            if year_match:
                yy = year_match.group(0)
                if len(yy) == 2:
                    yy = "20" + yy
            else:
                yy = str(current_year)  # If year missing
            return f"{num}-{yy}"

    # 2) Numeric month-year (1/2026, 01-2026, 1.26 etc)
    match = re.match(r"^(\d{1,2})[-\/\. ](\d{2,4})$", text)
    if match:
        mm, yy = match.groups()
        if len(yy) == 2:
            yy = "20" + yy
        return f"{int(mm):02d}-{yy}"

    return "INVALID"


# Webhook handler
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    intent_name = data['queryResult']['intent']['displayName']
    params = data['queryResult']['parameters']
    query_text = data['queryResult'].get('queryText', '')
    session = data['session']

    # Initialize user session
    if session not in user_sessions:
        user_sessions[session] = {}

    user_data = user_sessions[session]

    # ==========================================================
    # DESTINATION INTENT
    # ==========================================================
    if "destination" in intent_name.lower():
        city = params.get('city')
        country = params.get('country')
        destination = city or country or ""
        if city and country:
            destination = f"{city}, {country}"

        user_data["destination"] = clean(destination)

        return jsonify({
            "fulfillmentText": f"Got it! You're planning a trip to {destination}. "
                               "Which month and year would you like to travel? (e.g., Jan 2026)"
        })

    # ==========================================================
    # DATE INTENT (Month + Year ONLY)
    # ==========================================================
    elif "date" in intent_name.lower():
        travel_date = normalize_month_year(query_text)

        if travel_date == "INVALID":
            return jsonify({
                "fulfillmentText": "Please enter your travel month in a valid format like: "
                                   "Jan 2026, January 2026, 01-2026, or 1/2026."
            })

        user_data["travel_date"] = travel_date

        return jsonify({
            "fulfillmentText": f"Perfect! Your travel month is {travel_date}. "
                               "How many people will be going?"
        })

    # ==========================================================
    # PAX INTENT
    # ==========================================================
    elif "pax" in intent_name.lower():
        pax = params.get('number')
        if isinstance(pax, list) and pax:
            pax = pax[0]
        user_data["pax"] = clean(pax)

        return jsonify({
            "fulfillmentText": f"Great! Noted {pax} travelers. "
                               "Can I have your name, email, and phone number?"
        })

    # ==========================================================
    # CONTACT INTENT
    # ==========================================================
    elif "contact" in intent_name.lower():
        name = params.get('name')
        email = params.get('email')
        phone = params.get('phone-number') or params.get('phone')

        user_data["name"] = clean(name)
        user_data["email"] = clean(email)
        user_data["phone"] = clean(phone)

        # Write data to Google Sheet
        sheet = get_gsheet()
        sheet.append_row([
            user_data.get("name", ""),
            user_data.get("destination", ""),
            user_data.get("travel_date", ""),
            user_data.get("pax", ""),
            user_data.get("email", ""),
            user_data.get("phone", "")
        ])

        # Clear session
        user_sessions.pop(session, None)

        return jsonify({
            "fulfillmentText":
                f"Thanks {user_data.get('name')}! Your trip to "
                f"{user_data.get('destination')} in {user_data.get('travel_date')} "
                f"for {user_data.get('pax')} people has been recorded. "
                "We'll contact you soon."
        })

    # ==========================================================
    # DEFAULT FALLBACK
    # ==========================================================
    return jsonify({
        "fulfillmentText": "I'm not sure what details to save. Can you please repeat?"
    })


@app.route('/')
def home():
    return "✅ Travel Bot Backend connected with Google Sheets & session memory!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
