import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Explicitly allow ALL origins (*) on ALL routes (/*)
CORS(app, resources={r"/*": {"origins": "*"}})

limiter = Limiter(get_remote_address, app=app, default_limits=[])

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
TO_EMAIL = os.getenv("TO_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL")


@app.route('/send-email', methods=['POST'])
@limiter.limit("5 per hour")
def send_email():
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    if data.get('honeypot'):
        return jsonify({"message": "ok"}), 200

    # Extract new fields
    name = data.get('name', '').strip()
    contact_type = data.get('contactType', '').strip()
    contact_method = data.get('contactMethod', '').strip()
    from_location = data.get('from', '').strip()
    to_location = data.get('to', '').strip()
    cargo_type = data.get('cargoType', '').strip()
    estimated_tonnage = data.get('estimatedTonnage', '').strip()
    preferred_departure_date = data.get('preferredDepartureDate', '').strip()
    arrival_deadline = data.get('arrivalDeadline', '').strip()
    cargo_details = data.get('cargoDetails', '').strip()
    message = data.get('message', '').strip()

    # Basic Validation
    if not name or not contact_method:
        return jsonify({"error": "Missing required fields"}), 400

    # Validate email only if contactType is email
    if contact_type.lower() == 'email':
        if '@' not in contact_method or '.' not in contact_method:
            return jsonify({"error": "Invalid email address"}), 400

    if len(message) > 5000 or len(cargo_details) > 5000 or len(name) > 200:
        return jsonify({"error": "Input too long"}), 400

    if not RESEND_API_KEY:
        return jsonify({"error": "Server misconfiguration: RESEND_API_KEY is not set"}), 500

    # Generate a subject since it's no longer provided
    subject = f"New Cargo Inquiry from {name}"

    plain_text = (
        f"Name: {name}\n"
        f"Contact Type: {contact_type}\n"
        f"Contact Method: {contact_method}\n"
        f"From: {from_location}\n"
        f"To: {to_location}\n"
        f"Cargo Type: {cargo_type}\n"
        f"Estimated Tonnage: {estimated_tonnage}\n"
        f"Preferred Departure: {preferred_departure_date}\n"
        f"Arrival Deadline: {arrival_deadline}\n"
        f"Cargo Details: {cargo_details}\n"
        f"Message: {message}"
    )

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f4f4f4; padding: 20px;">
      <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
        <h2 style="color: #1a1a1a; margin-top: 0; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">
          New Cargo Inquiry — Ascent Airways
        </h2>
        <table style="width: 100%; font-size: 15px; color: #333333; border-collapse: collapse;">
          <tr>
            <td style="padding: 6px 0; font-weight: bold; width: 180px;">Name:</td>
            <td style="padding: 6px 0;">{name}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Contact Type:</td>
            <td style="padding: 6px 0;">{contact_type.capitalize()}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Contact Method:</td>
            <td style="padding: 6px 0;">{contact_method}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">From:</td>
            <td style="padding: 6px 0;">{from_location}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">To:</td>
            <td style="padding: 6px 0;">{to_location}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Cargo Type:</td>
            <td style="padding: 6px 0;">{cargo_type}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Est. Tonnage:</td>
            <td style="padding: 6px 0;">{estimated_tonnage}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Departure Date:</td>
            <td style="padding: 6px 0;">{preferred_departure_date}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-weight: bold;">Arrival Deadline:</td>
            <td style="padding: 6px 0;">{arrival_deadline}</td>
          </tr>
        </table>
        
        <h3 style="color: #1a1a1a; margin-top: 25px; margin-bottom: 10px; font-size: 16px;">Cargo Details:</h3>
        <p style="color: #333333; font-size: 15px; line-height: 1.6; white-space: pre-line; background: #f9f9f9; padding: 12px; border-radius: 4px; border: 1px solid #eeeeee;">
          {cargo_details if cargo_details else 'No cargo details provided.'}
        </p>

        <h3 style="color: #1a1a1a; margin-top: 20px; margin-bottom: 10px; font-size: 16px;">Additional Message:</h3>
        <p style="color: #333333; font-size: 15px; line-height: 1.6; white-space: pre-line; background: #f9f9f9; padding: 12px; border-radius: 4px; border: 1px solid #eeeeee;">
          {message if message else 'No additional message provided.'}
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;">
        <p style="color: #999999; font-size: 12px;">
          Sent automatically from the contact form.
        </p>
      </div>
    </div>
    """

    resend_payload = {
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": subject,
        "html": html_body,
        "text": plain_text
    }

    # Only set 'reply_to' if the contact method provided is a valid email
    if contact_type.lower() == 'email' and '@' in contact_method:
        resend_payload["reply_to"] = contact_method

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json=resend_payload,
            timeout=10
        )
    except requests.RequestException as e:
        return jsonify({"error": "Failed to reach email provider", "details": str(e)}), 502

    if response.status_code >= 400:
        return jsonify({"error": "Failed to send email", "details": response.text}), 502

    return jsonify({"message": "Email successfully sent"}), 200


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Too many requests. Please try again later."}), 429


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
