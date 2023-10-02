from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

ACCOUNT_SID = ''
AUTH_TOKEN = ''
TWILIO_PHONE_NUMBER = '' # Format: 'whatsapp:+1234567890'

# MongoDB setup
client = MongoClient('localhost', 27017)
db = client['notbot_db']
reminders_collection = db['reminders']

def check_and_send_reminders():
    now = datetime.now()
    due_reminders = reminders_collection.find({
        'reminder_time': {'$lte': now}
    })

    for reminder in due_reminders:
        message = reminder['message']
        to_number = reminder['to_number']
        
        # Send reminder via Twilio API
        send_message_via_twilio(to_number, message)
        
        # Delete reminder after sending
        reminders_collection.delete_one({'_id': reminder['_id']})

def send_message_via_twilio(to, message):
    twilio_url = "https://api.twilio.com/2010-04-01/Accounts/"+ACCOUNT_SID+"/Messages.json"
    auth = (ACCOUNT_SID, AUTH_TOKEN)
    data = {
        'From': TWILIO_PHONE_NUMBER,
        'To': to,
        'Body': message
    }
    requests.post(twilio_url, data=data, auth=auth)

@app.route('/incoming', methods=['POST'])
def incoming_message():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.startswith('remindme'):
        _, date, time, *message_parts = incoming_msg.split()
        message_text = " ".join(message_parts)
        reminder_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')

        reminders_collection.insert_one({
            'to_number': from_number,
            'message': message_text,
            'reminder_time': reminder_time
        })

        msg.body(f"Reminder set for {date} at {time}")
    else:
        msg.body("Invalid command. Use 'remindme YYYY-MM-DD HH:MM Your Message'.")

    return str(resp)

# Initialize scheduler with your preferred run time
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_and_send_reminders, trigger="interval", minutes=1)  # Set the interval to your preference
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)
