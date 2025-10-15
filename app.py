from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# --- Database connection ---
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# --- Webhook route for Dialogflow ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    params = data['queryResult']['parameters']

    destination = params.get('destination')
    travel_date = params.get('travel_date')
    pax = params.get('pax')
    contact = params.get('contact')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO travel_inquiries (destination, travel_date, pax, contact)
        VALUES (%s, %s, %s, %s)
    """, (destination, travel_date, pax, contact))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'fulfillmentText': f"Got it! Trip to {destination} saved. We'll contact you soon."})

# --- Home route ---
@app.route('/')
def home():
    return "Travel Bot Backend is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)