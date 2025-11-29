import os
import stripe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import csv
from io import StringIO

app = Flask(__name__)
CORS(app)

# Environment variables
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
OWNER_EMAIL = os.getenv('OWNER_EMAIL')
FROM_EMAIL = os.getenv('FROM_EMAIL')

# Firebase credentials from environment
firebase_creds = {
    "type": "service_account",
    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv('FIREBASE_CERT_URL')
}

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()
stripe.api_key = STRIPE_SECRET_KEY

# City to price mapping (you'll add real price IDs after creating them in Stripe)
CITY_PRICE_MAP = {
    'price_NASHVILLE_TEST_ID': 'Nashville',
    'price_CHATTANOOGA_TEST_ID': 'Chattanooga',
    'price_AUSTIN_TEST_ID': 'Austin',
    'price_SANANTONIO_TEST_ID': 'San Antonio',
    'price_HOUSTON_TEST_ID': 'Houston',
    'price_CHARLOTTE_TEST_ID': 'Charlotte',
    'price_PHOENIX_TEST_ID': 'Phoenix',
    'price_BUNDLE_TEST_ID': 'all-cities'
}

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        city = data.get('city')
        price_id = data.get('price_id')
        
        # Get frontend URL from env or use default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{frontend_url}/success.html',
            cancel_url=f'{frontend_url}',
            metadata={
                'city': city
            }
        )
        
        return jsonify({'url': session.url})
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle successful checkout
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get customer details
        customer_id = session['customer']
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']
        
        # Get subscription to find the price ID
        subscription_id = session['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription['items']['data'][0]['price']['id']
        
        # Map price ID to city
        city = CITY_PRICE_MAP.get(price_id, session['metadata'].get('city', 'Unknown'))
        
        # Save to Firestore
        db.collection('subscribers').document(customer_id).set({
            'email': email,
            'city': city,
            'stripe_customer_id': customer_id,
            'subscription_id': subscription_id,
            'active': True,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f"New subscriber: {email} for {city}")
    
    # Handle failed payment
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        customer_id = invoice['customer']
        
        # Update subscriber to inactive
        db.collection('subscribers').document(customer_id).update({
            'active': False,
            'payment_failed_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f"Payment failed for customer: {customer_id}")
    
    # Handle subscription deleted/cancelled
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        
        # Update subscriber to inactive
        db.collection('subscribers').document(customer_id).update({
            'active': False,
            'cancelled_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f"Subscription cancelled for customer: {customer_id}")
    
    return jsonify({'status': 'success'}), 200

def get_leads_for_city(city, count=10):
    """Get leads for a city - replace with real scraper calls"""
    # For now, using mock data - replace with actual scraper imports
    leads = []
    for i in range(count):
        leads.append({
            'permit_number': f'P{city[:3].upper()}{1000+i}',
            'address': f'{100+i} Main St, {city}',
            'owner_name': f'Owner {i+1}',
            'permit_type': ['Building', 'Electrical', 'Plumbing', 'Mechanical'][i % 4],
            'permit_value': f'${(i+1) * 25000:,}',
            'issue_date': datetime.now().strftime('%Y-%m-%d')
        })
    return leads

def generate_csv_string(leads):
    """Convert leads list to CSV string"""
    if not leads:
        return ""
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=leads[0].keys())
    writer.writeheader()
    writer.writerows(leads)
    return output.getvalue()

def generate_html_table(leads):
    """Convert leads to HTML table"""
    if not leads:
        return "<p>No leads available today.</p>"
    
    html = """
    <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
        <thead>
            <tr style="background-color: #667eea; color: white;">
    """
    
    for key in leads[0].keys():
        html += f"<th style='padding: 12px; text-align: left; border: 1px solid #ddd;'>{key.replace('_', ' ').title()}</th>"
    
    html += "</tr></thead><tbody>"
    
    for i, lead in enumerate(leads):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        html += f"<tr style='background-color: {bg_color};'>"
        for value in lead.values():
            html += f"<td style='padding: 10px; border: 1px solid #ddd;'>{value}</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html

def send_daily_leads():
    """Run daily at 8 AM Central - send leads to all active subscribers"""
    print(f"Starting daily lead distribution at {datetime.now()}")
    
    try:
        # Get all active subscribers
        subscribers_ref = db.collection('subscribers').where('active', '==', True)
        subscribers = subscribers_ref.get()
        
        # Group by city
        city_subscribers = {}
        all_subscribers_data = []
        
        for sub in subscribers:
            data = sub.to_dict()
            city = data['city']
            email = data['email']
            
            if city not in city_subscribers:
                city_subscribers[city] = []
            city_subscribers[city].append(email)
            
            all_subscribers_data.append({
                'email': email,
                'city': city,
                'customer_id': data['stripe_customer_id'],
                'created_at': data.get('created_at', 'N/A')
            })
        
        # Send leads to each city's subscribers
        for city, emails in city_subscribers.items():
            if city == 'all-cities':
                # Bundle subscribers get leads from all cities
                all_cities = ['Nashville', 'Chattanooga', 'Austin', 'San Antonio', 'Houston', 'Charlotte', 'Phoenix']
                all_leads = []
                for c in all_cities:
                    leads = get_leads_for_city(c)
                    all_leads.extend(leads)
                
                html_table = generate_html_table(all_leads)
                subject = f'Your Daily All Cities Contractor Leads - {datetime.now().strftime("%m/%d/%Y")}'
                body_city = "All Cities"
                
                for email in emails:
                    try:
                        message = Mail(
                            from_email=Email(FROM_EMAIL),
                            to_emails=To(email),
                            subject=subject,
                            html_content=f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px;">
                                <h2 style="color: #667eea;">Your Daily {body_city} Leads</h2>
                                <p>Here are your fresh contractor leads for {datetime.now().strftime("%B %d, %Y")}:</p>
                                {html_table}
                                <hr style="margin: 30px 0;">
                                <p style="color: #718096; font-size: 14px;">
                                    Need to cancel? Click the manage subscription link in your Stripe receipt.
                                </p>
                            </body>
                            </html>
                            """
                        )
                        
                        sg = SendGridAPIClient(SENDGRID_API_KEY)
                        sg.send(message)
                        print(f"Sent all cities leads to {email}")
                    except Exception as e:
                        print(f"Error sending to {email}: {e}")
            else:
                # Individual city subscribers
                leads = get_leads_for_city(city)
                html_table = generate_html_table(leads)
                subject = f'Your Daily {city} Contractor Leads - {datetime.now().strftime("%m/%d/%Y")}'
                body_city = city
                
                for email in emails:
                    try:
                        message = Mail(
                            from_email=Email(FROM_EMAIL),
                            to_emails=To(email),
                            subject=subject,
                            html_content=f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; padding: 20px;">
                                <h2 style="color: #667eea;">Your Daily {body_city} Leads</h2>
                                <p>Here are your fresh contractor leads for {datetime.now().strftime("%B %d, %Y")}:</p>
                                {html_table}
                                <hr style="margin: 30px 0;">
                                <p style="color: #718096; font-size: 14px;">
                                    Need to cancel? Click the manage subscription link in your Stripe receipt.
                                </p>
                            </body>
                            </html>
                            """
                        )
                        
                        sg = SendGridAPIClient(SENDGRID_API_KEY)
                        sg.send(message)
                        print(f"Sent leads to {email} for {city}")
                    except Exception as e:
                        print(f"Error sending to {email}: {e}")
        
        # Send master CSV to owner
        if all_subscribers_data:
            csv_content = generate_csv_string(all_subscribers_data)
            
            message = Mail(
                from_email=Email(FROM_EMAIL),
                to_emails=To(OWNER_EMAIL),
                subject=f'Daily Subscriber Report - {datetime.now().strftime("%m/%d/%Y")}',
                html_content=f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Daily Active Subscribers</h2>
                    <p>Total Active: {len(all_subscribers_data)}</p>
                    <p>Breakdown:</p>
                    <ul>
                        {''.join([f'<li>{city}: {len(emails)} subscribers</li>' for city, emails in city_subscribers.items()])}
                    </ul>
                    <p>Full subscriber list attached as CSV.</p>
                </body>
                </html>
                """
            )
            
            # Attach CSV
            import base64
            encoded_csv = base64.b64encode(csv_content.encode()).decode()
            message.attachment = {
                'content': encoded_csv,
                'filename': f'subscribers_{datetime.now().strftime("%Y%m%d")}.csv',
                'type': 'text/csv',
                'disposition': 'attachment'
            }
            
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
            print(f"Sent master report to {OWNER_EMAIL}")
        
        print(f"Daily lead distribution completed successfully")
        
    except Exception as e:
        print(f"Error in daily lead distribution: {e}")

# Schedule daily job at 8 AM Central
scheduler = BackgroundScheduler()
central = pytz.timezone('US/Central')
scheduler.add_job(
    func=send_daily_leads,
    trigger='cron',
    hour=8,
    minute=0,
    timezone=central
)
scheduler.start()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/manual-send', methods=['POST'])
def manual_send():
    """Manual trigger for testing - remove in production"""
    auth = request.headers.get('Authorization')
    if auth != f"Bearer {os.getenv('ADMIN_SECRET', 'test123')}":
        return jsonify({'error': 'Unauthorized'}), 401
    
    send_daily_leads()
    return jsonify({'status': 'sent'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
