import os
import stripe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import csv
from io import StringIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment variables
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
OWNER_EMAIL = os.getenv('OWNER_EMAIL')
FROM_EMAIL = os.getenv('FROM_EMAIL')

# Firebase credentials from service account key file
if not firebase_admin._apps:
    cred = credentials.Certificate('serviceAccountKey.json')
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
        
        # Check if this is a subscription or one-time payment
        if session.get('mode') == 'subscription':
            # Handle subscription payment
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
            
            # Create Firebase Auth user account
            try:
                user = auth.create_user(
                    email=email,
                    email_verified=False,
                    display_name=email.split('@')[0]
                )
                
                # Create user profile in Firestore
                db.collection('users').document(user.uid).set({
                    'email': email,
                    'stripe_customer_id': customer_id,
                    'subscription_active': True,
                    'city': city,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'role': 'subscriber'
                })
                
                print(f"✅ Created Firebase Auth user for subscriber: {email}")
            except Exception as e:
                print(f"⚠️  Could not create Firebase Auth user for {email}: {e}")
            
            print(f"New subscriber: {email} for {city}")
        
        elif session.get('mode') == 'payment':
            # Handle one-time payment (like our $1 test)
            customer_email = session.get('customer_details', {}).get('email')
            if not customer_email:
                # For one-time payments without customer creation
                customer_email = session.get('metadata', {}).get('email', 'test@example.com')
            
            # Get payment details
            amount_total = session.get('amount_total', 0) / 100  # Convert from cents

            # For $97 All Cities Bundle
            if amount_total == 97.00:
                city = 'All Cities Bundle'
                all_cities = ['Nashville', 'Chattanooga', 'Austin', 'San Antonio', 'Houston', 'Charlotte', 'Phoenix']

                # Create a customer ID for Firebase
                customer_id = f"allcities_{customer_email.replace('@', '_').replace('.', '_')}_{int(datetime.now().timestamp())}"

                # Save to Firestore
                db.collection('subscribers').document(customer_id).set({
                    'email': customer_email,
                    'city': city,
                    'cities': all_cities,
                    'stripe_customer_id': customer_id,
                    'subscription_id': session.get('subscription'),
                    'active': True,
                    'amount_paid': amount_total,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                
                # Create Firebase Auth user account
                try:
                    user = auth.create_user(
                        email=customer_email,
                        email_verified=False,
                        display_name=customer_email.split('@')[0]
                    )
                    
                    # Create user profile in Firestore
                    db.collection('users').document(user.uid).set({
                        'email': customer_email,
                        'stripe_customer_id': customer_id,
                        'subscription_active': True,
                        'city': city,
                        'cities': all_cities,
                        'amount_paid': amount_total,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'role': 'subscriber'
                    })
                    
                    print(f"✅ Created Firebase Auth user for All Cities Bundle subscriber: {customer_email}")
                except Exception as e:
                    print(f"⚠️  Could not create Firebase Auth user for {customer_email}: {e}")

                # Create bundle folder
                import os
                bundle_dir = os.path.join('leads', 'allcitiesbundle')
                os.makedirs(bundle_dir, exist_ok=True)

                # Create client file with leads from all cities
                client_data = f"""New All Cities Bundle Subscriber: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Email: {customer_email}
Plan: All Cities Bundle
Cities: {', '.join(all_cities)}
Amount Paid: ${amount_total}
Subscription Active: Yes

Welcome! You'll receive daily contractor leads from ALL 7 cities starting tomorrow at 8 AM.

"""

                # Collect leads from all cities
                all_leads = []
                for city_name in all_cities:
                    city_leads = get_leads_for_city(city_name, count=5)
                    all_leads.extend(city_leads)

                    # Add to client file
                    client_data += f"\n--- {city_name} Sample Leads ---\n"
                    for lead in city_leads:
                        client_data += f"""
Permit: {lead['permit_number']}
Address: {lead['address']}
Owner: {lead.get('owner_name', 'N/A')}
Type: {lead['permit_type']}
Value: {lead['permit_value']}
Date: {lead['issue_date']}
"""

                # Save to file
                filename = f"subscriber_{int(datetime.now().timestamp())}.txt"
                filepath = os.path.join(bundle_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(client_data)

                print(f"✅ Created Firebase record and local file for All Cities Bundle subscriber: {customer_email}")

                # Generate HTML tables for each city
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #667eea;">Welcome to Contractor Leads - All Cities Bundle! 🎉</h2>
                    <p>Thank you for subscribing to our All Cities Bundle! You now have access to fresh leads from all 7 cities.</p>
                    <p><strong>Your cities:</strong> {', '.join(all_cities)}</p>
                    <p>Below are sample leads from each city. You'll receive daily leads at 8 AM.</p>
                    
                    <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <h3 style="color: #0ea5e9; margin-top: 0;">🔐 Access Your Dashboard</h3>
                        <p>You can now log into your dashboard to view all your leads and manage your account:</p>
                        <p><strong>Dashboard URL:</strong> <a href="http://localhost:8080/dashboard/dashboard.html" style="color: #0ea5e9;">http://localhost:8080/dashboard/dashboard.html</a></p>
                        <p><strong>Email:</strong> {customer_email}</p>
                        <p><strong>Password:</strong> You'll need to create a password when you first log in.</p>
                        <p style="color: #dc2626; font-weight: bold;">First-time login: Click "Create Account" on the login page to set your password.</p>
                    </div>
                """

                for city_name in all_cities:
                    city_leads = get_leads_for_city(city_name, count=3)
                    if city_leads:
                        html_content += f"<h3 style='color: #667eea; margin-top: 30px;'>{city_name}</h3>"
                        html_content += generate_html_table(city_leads)

                html_content += """
                    <hr style="margin: 30px 0;">
                    <p style="color: #718096; font-size: 14px;">
                        Your All Cities Bundle subscription is now active. Daily leads from all 7 cities will be delivered to this email address at 8 AM.
                    </p>
                </body>
                </html>
                """

                try:
                    message = Mail(
                        from_email=Email(FROM_EMAIL),
                        to_emails=To(customer_email),
                        subject='Welcome to Contractor Leads - All Cities Bundle! 🎉',
                        html_content=html_content
                    )

                    sg = SendGridAPIClient(SENDGRID_API_KEY)
                    sg.send(message)
                    print(f"✅ Sent All Cities Bundle welcome email to {customer_email}")
                except Exception as e:
                    print(f"❌ Error sending welcome email to {customer_email}: {e}")

            # For $47 payments (Austin, San Antonio, Houston, etc.)
            elif amount_total == 47.00:
                # Determine city from session metadata or default to Austin
                city = session.get('metadata', {}).get('city', 'Austin')

                # Create a customer ID for Firebase
                city_slug = city.lower().replace(' ', '')
                customer_id = f"{city_slug}_{customer_email.replace('@', '_').replace('.', '_')}_{int(datetime.now().timestamp())}"

                # Save to Firestore
                db.collection('subscribers').document(customer_id).set({
                    'email': customer_email,
                    'city': city,
                    'stripe_customer_id': customer_id,
                    'subscription_id': session.get('subscription'),
                    'active': True,
                    'amount_paid': amount_total,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                
                # Create Firebase Auth user account
                try:
                    user = auth.create_user(
                        email=customer_email,
                        email_verified=False,
                        display_name=customer_email.split('@')[0]
                    )
                    
                    # Create user profile in Firestore
                    db.collection('users').document(user.uid).set({
                        'email': customer_email,
                        'stripe_customer_id': customer_id,
                        'subscription_active': True,
                        'city': city,
                        'amount_paid': amount_total,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'role': 'subscriber'
                    })
                    
                    print(f"✅ Created Firebase Auth user for {city} subscriber: {customer_email}")
                except Exception as e:
                    print(f"⚠️  Could not create Firebase Auth user for {customer_email}: {e}")

                # Add to local city folder (create if doesn't exist)
                import os
                city_dir = os.path.join('leads', city_slug)
                os.makedirs(city_dir, exist_ok=True)

                # Create a client file
                client_data = f"""New {city} Subscriber: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Email: {customer_email}
City: {city}
Amount Paid: ${amount_total}
Subscription Active: Yes

Welcome! You'll receive daily contractor leads starting tomorrow at 8 AM.
"""
                
                # Get sample leads and add to file
                leads = get_leads_for_city(city, count=5)
                for lead in leads:
                    client_data += f"""
Permit: {lead['permit_number']}
Address: {lead['address']}
Owner: {lead['owner_name']}
Type: {lead['permit_type']}
Value: {lead['permit_value']}
Date: {lead['issue_date']}
"""
                
                # Save to file
                filename = f"subscriber_{int(datetime.now().timestamp())}.txt"
                filepath = os.path.join(city_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(client_data)

                print(f"✅ Created Firebase record and local file for {city} subscriber: {customer_email}")

                # Get sample leads for welcome email
                html_table = generate_html_table(leads)

                try:
                    message = Mail(
                        from_email=Email(FROM_EMAIL),
                        to_emails=To(customer_email),
                        subject=f'Welcome to Contractor Leads - {city}!',
                        html_content=f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; padding: 20px;">
                            <h2 style="color: #667eea;">Welcome to Contractor Leads - {city}!</h2>
                            <p>Thank you for subscribing! Here are your first 5 sample leads. You'll receive fresh leads daily at 8 AM.</p>
                            
                            <div style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 20px; margin: 20px 0;">
                                <h3 style="color: #0ea5e9; margin-top: 0;">🔐 Access Your Dashboard</h3>
                                <p>You can now log into your dashboard to view all your leads and manage your account:</p>
                                <p><strong>Dashboard URL:</strong> <a href="http://localhost:8080/dashboard/dashboard.html" style="color: #0ea5e9;">http://localhost:8080/dashboard/dashboard.html</a></p>
                                <p><strong>Email:</strong> {customer_email}</p>
                                <p><strong>Password:</strong> You'll need to create a password when you first log in.</p>
                                <p style="color: #dc2626; font-weight: bold;">First-time login: Click "Create Account" on the login page to set your password.</p>
                            </div>
                            
                            {html_table}
                            <hr style="margin: 30px 0;">
                            <p style="color: #718096; font-size: 14px;">
                                Your subscription is now active. Daily leads will be delivered to this email address.
                            </p>
                        </body>
                        </html>
                        """
                    )
                    
                    sg = SendGridAPIClient(SENDGRID_API_KEY)
                    sg.send(message)
                    print(f"✅ Sent welcome email to {customer_email}")
                except Exception as e:
                    print(f"❌ Error sending welcome email to {customer_email}: {e}")
            
            print(f"One-time payment completed: ${amount_total} to {customer_email}")
    
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
    """Get REAL leads from scraped CSV files"""
    leads = []

    try:
        # Get the most recent CSV file for the city
        city_lower = city.lower()
        leads_dir = f'leads/{city_lower}'

        if not os.path.exists(leads_dir):
            print(f"⚠️  No leads directory found for {city}")
            return []

        # Find most recent date folder
        date_folders = [d for d in os.listdir(leads_dir) if os.path.isdir(os.path.join(leads_dir, d))]
        if not date_folders:
            print(f"⚠️  No date folders found for {city}")
            return []

        # Sort by date (most recent first)
        date_folders.sort(reverse=True)
        most_recent_folder = date_folders[0]

        # Look for CSV file in that folder
        csv_path = os.path.join(leads_dir, most_recent_folder, f'{most_recent_folder}_{city_lower}.csv')

        if not os.path.exists(csv_path):
            print(f"⚠️  CSV file not found: {csv_path}")
            return []

        # Read CSV file
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            all_leads = list(reader)

        # Return requested count
        for lead_data in all_leads[:count]:
            leads.append({
                'permit_number': lead_data.get('permit_number', 'N/A'),
                'address': lead_data.get('address', 'N/A'),
                'permit_type': lead_data.get('type', 'N/A'),
                'permit_value': lead_data.get('value', 'N/A'),
                'issue_date': lead_data.get('issued_date', datetime.now().strftime('%Y-%m-%d'))
            })

        print(f"✅ Loaded {len(leads)} real leads for {city} from {csv_path}")

    except Exception as e:
        print(f"❌ Error loading leads for {city}: {e}")
        return []

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

@app.route('/create-portal-session', methods=['POST'])
def create_portal_session():
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Create customer portal session
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url='http://localhost:8081/index.html'  # Return to main page after portal
        )
        
        return jsonify({'url': session.url})
    
    except Exception as e:
        print(f"Error creating portal session: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
