from flask import Flask, request, jsonify
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# Temporary memory for active sessions
user_sessions = {}


# -------------------------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------------------------
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        raise Exception("❌ GOOGLE_SHEETS_CREDENTIALS environment variable not set.")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("travel-bot-data").sheet1
    return sheet


# -------------------------------------------
# CLEAN VALUES
# -------------------------------------------
def clean(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


# -------------------------------------------
# FIXED DATE EXTRACTOR (Main Fix)
# -------------------------------------------
def get_travel_dates(params, query_text):

    # CASE 1: Dialogflow returns a DATE PERIOD list
    date_period = params.get("date-period")
    if isinstance(date_period, list) and len(date_period) > 0:
        dp = date_period[0]
        start = dp.get("startDate")
        end = dp.get("endDate")
        if start and end:
            return f"{start} → {end}"

    # CASE 2: User enters only day + month (Dialogflow returns date)
    date_alt = params.get("date_alt")
    if date_alt:
        try:
            dt = datetime.fromisoformat(date_alt.replace("Z", ""))
            # Convert to full month range
            first = f"{dt.year}-{dt.month:02d}-01"
            last = f"{dt.year}-{dt.month:02d}-31"
            return f"{first} → {last}"
        except:
            pass

    # CASE 3: Keyword month detection (fallback)
    query_text = query_text.lower()
    current_year = datetime.now().year
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    for m_name, m_num in months.items():
        if m_name in query_text:
            return f"{current_year}-{m_num}-01 → {current_year}-{m_num}-31"

    return "Unclear date"


# -------------------------------------------
# WEBHOOK
# -------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    intent = data["queryResult"]["intent"]["displayName"].lower()
    params = data["queryResult"]["parameters"]
    query_text = data["queryResult"].get("queryText", "")
    session = data["session"]

    if session not in user_sessions:
        user_sessions[session] = {}
    user = user_sessions[session]

    # -------------------------------------------
    # DESTINATION INTENT
    # -------------------------------------------
    if "destination" in intent:
        city = params.get("city")
        country = params.get("country")
        destination = city or country or "your destination"
        user["destination"] = clean(destination)

        return jsonify({
            "fulfillmentText": f"Got it! You're planning a trip to {destination}. When would you like to travel?"
        })

    # -------------------------------------------
    # DATE INTENT
    # -------------------------------------------
    elif "date" in intent:
        travel_date = get_travel_dates(params, query_text)
        user["travel_date"] = clean(travel_date)

        return jsonify({
            "fulfillmentText": f"Perfect! When you travel on {travel_date}. How many people will be going?"
        })

    # -------------------------------------------
    # PAX INTENT
    # -------------------------------------------
    elif "pax" in intent:
        number = params.get("number")
        pax_type = params.get("pax_type")  # adult / child / infant etc.

        if number:
            pax = f"{number} {pax_type}" if pax_type else number
        else:
            pax = clean(params.get("pax_entity"))

        user["pax"] = clean(pax)

        return jsonify({
            "fulfillmentText": f"Great! Noted {pax} travelers. Can I have your name, email, and phone number?"
        })

    # -------------------------------------------
    # CONTACT DETAILS INTENT
    # -------------------------------------------
    elif "contact" in intent:
        name = params.get("name")
        email = params.get("email")
        phone = params.get("phone")

        user["name"] = clean(name)
        user["email"] = clean(email)
        user["phone"] = clean(phone)

        # Save in Google Sheet
        sheet = get_gsheet()
        sheet.append_row([
            user.get("name", ""),
            user.get("destination", ""),
            user.get("travel_date", ""),
            user.get("pax", ""),
            user.get("email", ""),
            user.get("phone", "")
        ])

        # Clear session
        user_sessions.pop(session, None)

        return jsonify({
            "fulfillmentText":
                f"Thanks {name}! Your trip to {user.get('destination')} "
                f"on {user.get('travel_date')} for {user.get('pax')} people "
                f"has been recorded. We'll contact you soon."
        })

    return jsonify({"fulfillmentText": "Could you repeat that please?"})


@app.route("/")
def home():
    return "✅ Travel Bot Backend connected!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
