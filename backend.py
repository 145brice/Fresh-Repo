import os
import stripe
from flask import Flask, request, send_from_directory, jsonify, render_template_string, make_response, redirect
import subprocess
import json
import datetime
import pandas as pd
import time
import random
import csv
from io import StringIO
import resend
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import firebase_admin
from firebase_admin import credentials, firestore
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === SETUP ===
app = Flask(__name__, static_folder='../')  # Frontend files are in root

# Environment variables - set these in .env or terminal
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')
RESEND_API_KEY = os.getenv('RESEND_API_KEY', 're_...')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'SG....')
OWNER_EMAIL = os.getenv('OWNER_EMAIL', '145brice@gmail.com')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'leads@yourdomain.com')
ADMIN_SECRET = os.getenv('ADMIN_SECRET', 'admin123')

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY
resend.api_key = RESEND_API_KEY

# Firebase setup
cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Cities list - add new ones here
CITIES = ['nashville', 'chattanooga', 'austin', 'sanantonio', 'houston', 'charlotte', 'phoenix', 'dallas', 'raleigh']  # expand forever

# Create folders
os.makedirs('../Clients Subs/cities', exist_ok=True)
os.makedirs('../Clients Subs/leads', exist_ok=True)
os.makedirs('../Clients Subs/subs', exist_ok=True)

# === HTML TEMPLATES ===
HOME_HEADER = '''
<header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 0; position: fixed; top: 0; width: 100%; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 24px; font-weight: 800;">🏗️ Contractor Leads</div>
        <nav style="display: flex; gap: 20px; align-items: center;">
            <a href="/" style="color: white; text-decoration: none; font-weight: 500; padding: 8px 16px; border-radius: 6px; transition: background 0.3s;">Home</a>
            <a href="/login" style="color: white; text-decoration: none; font-weight: 500; padding: 8px 16px; border-radius: 6px; transition: background 0.3s;">Login</a>
            <a href="/signup" style="background: rgba(255,255,255,0.2); color: white; text-decoration: none; font-weight: 500; padding: 8px 16px; border-radius: 6px; transition: background 0.3s;">Sign Up</a>
        </nav>
    </div>
</header>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Contractor Leads</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        h1 { color: #1e293b; margin-bottom: 10px; }
        p { color: #64748b; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 5px; color: #374151; font-weight: 500; }
        input { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e2e8f0; 
            border-radius: 8px; 
            font-size: 16px;
        }
        input:focus { outline: none; border-color: #667eea; }
        .btn { 
            background: #667eea; 
            color: white; 
            padding: 12px 30px; 
            border: none; 
            border-radius: 8px; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer; 
            width: 100%;
            margin-top: 10px;
        }
        .btn:hover { background: #5a67d8; }
        .error { color: #e53e3e; margin-bottom: 15px; font-size: 14px; }
        .back-link { display: block; margin-top: 20px; color: #667eea; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Login to Your Dashboard</h1>
        <p>Access all your historical leads</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label for="email">Subscriber Email</label>
                <input type="email" id="email" name="email" required placeholder="your@email.com">
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
        
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
'''

SIGNUP_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up - Contractor Leads</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        h1 { color: #1e293b; margin-bottom: 10px; }
        p { color: #64748b; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 5px; color: #374151; font-weight: 500; }
        input { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e2e8f0; 
            border-radius: 8px; 
            font-size: 16px;
        }
        input:focus { outline: none; border-color: #667eea; }
        .btn { 
            background: #667eea; 
            color: white; 
            padding: 12px 30px; 
            border: none; 
            border-radius: 8px; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer; 
            width: 100%;
            margin-top: 10px;
        }
        .btn:hover { background: #5a67d8; }
        .error { color: #e53e3e; margin-bottom: 15px; font-size: 14px; }
        .back-link { display: block; margin-top: 20px; color: #667eea; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 Sign Up for Updates</h1>
        <p>Get notified when new cities are added</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        {% if success %}
        <div style="color: #059669; margin-bottom: 15px; font-size: 14px;">{{ success }}</div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required placeholder="your@email.com">
            </div>
            <button type="submit" class="btn">Sign Up</button>
        </form>
        
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Contractor Leads</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f8fafc;
            color: #1e293b;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { margin: 0; }
        .logout-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
        }
        .logout-btn:hover { background: rgba(255,255,255,0.3); }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number { font-size: 32px; font-weight: 800; color: #667eea; }
        .stat-label { color: #64748b; margin-top: 5px; }
        
        .date-section {
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .date-header {
            background: #f1f5f9;
            padding: 15px 20px;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            color: #374151;
        }
        
        .city-section {
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
            background: #f8fafc;
        }
        .city-header {
            padding: 10px 15px;
            font-weight: 600;
            color: #667eea;
            background: #e0e7ff;
        }
        
        .leads-table {
            width: 100%;
            border-collapse: collapse;
        }
        .leads-table th {
            background: #f8fafc;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e2e8f0;
        }
        .leads-table td {
            padding: 12px;
            border-bottom: 1px solid #f1f5f9;
        }
        .leads-table tr:hover { background: #f8fafc; }
        
        .permit-number { font-weight: 600; color: #667eea; }
        .address { color: #374151; }
        .permit-type { 
            background: #dbeafe; 
            color: #1e40af; 
            padding: 4px 8px; 
            border-radius: 4px; 
            font-size: 12px; 
            font-weight: 600; 
        }
        .value { font-weight: 700; color: #059669; }
        
        .no-leads {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 10px; text-align: center; }
            .stats { grid-template-columns: 1fr; }
            .leads-table { font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Your Contractor Leads Dashboard</h1>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ user_cities|length }}</div>
                <div class="stat-label">Cities Subscribed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ leads_by_date|length }}</div>
                <div class="stat-label">Days of Leads</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">
                    {% set total_leads = 0 %}
                    {% for date, cities in leads_by_date.items() %}
                        {% for city, leads in cities.items() %}
                            {% set total_leads = total_leads + leads|length %}
                        {% endfor %}
                    {% endfor %}
                    {{ total_leads }}
                </div>
                <div class="stat-label">Total Leads</div>
            </div>
        </div>
        
        {% if leads_by_date %}
            {% for date, cities in leads_by_date.items() %}
            <div class="date-section">
                <div class="date-header">📅 {{ date }}</div>
                
                {% for city, leads in cities.items() %}
                <div class="city-section">
                    <div class="city-header">{{ city.title() }} ({{ leads|length }} leads)</div>
                    
                    <table class="leads-table">
                        <thead>
                            <tr>
                                <th>Permit #</th>
                                <th>Address</th>
                                <th>Type</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for lead in leads %}
                            <tr>
                                <td><span class="permit-number">{{ lead.permit_number }}</span></td>
                                <td><span class="address">{{ lead.address }}</span></td>
                                <td><span class="permit-type">{{ lead.type }}</span></td>
                                <td><span class="value">{{ lead.value }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% endfor %}
            </div>
            {% endfor %}
        {% else %}
            <div class="no-leads">
                <h3>No leads yet</h3>
                <p>Your first daily leads will appear here tomorrow morning at 8 AM.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - Contractor Leads</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        h1 { color: #1e293b; margin-bottom: 10px; }
        p { color: #64748b; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 5px; color: #374151; font-weight: 500; }
        input { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e2e8f0; 
            border-radius: 8px; 
            font-size: 16px;
        }
        input:focus { outline: none; border-color: #dc2626; }
        .btn { 
            background: #dc2626; 
            color: white; 
            padding: 12px 30px; 
            border: none; 
            border-radius: 8px; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer; 
            width: 100%;
            margin-top: 10px;
        }
        .btn:hover { background: #b91c1c; }
        .error { color: #e53e3e; margin-bottom: 15px; font-size: 14px; }
        .back-link { display: block; margin-top: 20px; color: #dc2626; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Admin Access</h1>
        <p>View all scraped data across all cities</p>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="POST" action="/admin/login">
            <div class="form-group">
                <label for="secret">Admin Secret</label>
                <input type="password" id="secret" name="secret" required placeholder="Enter admin secret">
            </div>
            <button type="submit" class="btn">Access Admin Dashboard</button>
        </form>
        
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Contractor Leads</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f8fafc;
            color: #1e293b;
        }
        .header {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { margin: 0; }
        .logout-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
        }
        .logout-btn:hover { background: rgba(255,255,255,0.3); }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number { font-size: 32px; font-weight: 800; color: #dc2626; }
        .stat-label { color: #64748b; margin-top: 5px; }
        
        .section {
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .section-header {
            background: #f1f5f9;
            padding: 15px 20px;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            color: #374151;
        }
        
        .city-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        .city-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
        }
        .city-header {
            background: #f8fafc;
            padding: 12px 15px;
            font-weight: 600;
            color: #374151;
            border-bottom: 1px solid #e2e8f0;
        }
        .city-stats {
            padding: 10px 15px;
            display: flex;
            justify-content: space-between;
            font-size: 14px;
        }
        .city-files {
            max-height: 150px;
            overflow-y: auto;
        }
        .file-item {
            padding: 8px 15px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 12px;
            color: #64748b;
        }
        .file-item:last-child { border-bottom: none; }
        
        .leads-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .leads-table th {
            background: #f8fafc;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e2e8f0;
            cursor: pointer;
            user-select: none;
            position: relative;
        }
        .leads-table th:hover {
            background: #e2e8f0;
        }
        .leads-table th.sort-asc::after {
            content: ' ▲';
            font-size: 12px;
        }
        .leads-table th.sort-desc::after {
            content: ' ▼';
            font-size: 12px;
        }
        .leads-table td {
            padding: 8px 10px;
            border-bottom: 1px solid #f1f5f9;
        }
        .leads-table tr:hover { background: #f8fafc; }
        
        .permit-number { font-weight: 600; color: #dc2626; }
        .address { color: #374151; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        .permit-type { 
            background: #fee2e2; 
            color: #991b1b; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 11px; 
            font-weight: 600; 
        }
        .value { font-weight: 700; color: #059669; }
        
        .recent-activity {
            padding: 20px;
        }
        .activity-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        .activity-date { font-weight: 600; }
        .activity-cities { display: flex; gap: 10px; flex-wrap: wrap; }
        .activity-city {
            background: #dbeafe;
            color: #1e40af;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 10px; text-align: center; }
            .stats { grid-template-columns: 1fr; }
            .city-grid { grid-template-columns: 1fr; }
            .leads-table { font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 Admin Dashboard - All Contractor Leads</h1>
        <a href="/admin?logout=1" class="logout-btn">Logout</a>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ cities|length }}</div>
                <div class="stat-label">Total Cities</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_leads }}</div>
                <div class="stat-label">Total Leads Scraped</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ all_leads|length }}</div>
                <div class="stat-label">Days of Data</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">
                    {% set active_cities = 0 %}
                    {% for city, data in cities_data.items() %}
                        {% if data.leads %}
                            {% set active_cities = active_cities + 1 %}
                        {% endif %}
                    {% endfor %}
                    {{ active_cities }}
                </div>
                <div class="stat-label">Active Cities</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">📊 City Overview</div>
            <div class="city-grid">
                {% for city, data in cities_data.items() %}
                <div class="city-card">
                    <div class="city-header">{{ city.title() }}</div>
                    <div class="city-stats">
                        <span>{{ data.leads|length }} leads</span>
                        <span>{{ data.files|length }} files</span>
                    </div>
                    <div class="city-files">
                        {% for file in data.files[:5] %}
                        <div class="file-item">{{ file }}</div>
                        {% endfor %}
                        {% if data.files|length > 5 %}
                        <div class="file-item">... and {{ data.files|length - 5 }} more</div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">📅 Recent Activity (Last 7 Days)</div>
            <div class="recent-activity">
                {% for date, cities in recent_activity.items() %}
                <div class="activity-item">
                    <span class="activity-date">{{ date }}</span>
                    <div class="activity-cities">
                        {% for city, leads in cities.items() %}
                        <span class="activity-city">{{ city.title() }} ({{ leads|length }})</span>
                        {% endfor %}
                        {% if not cities %}
                        <span style="color: #64748b; font-style: italic;">No activity</span>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        {% if all_leads %}
        <div class="section">
            <div class="section-header">📋 All Leads by Date</div>
            {% for date, cities in all_leads.items() %}
            <div style="margin-bottom: 30px;">
                <h3 style="padding: 15px 20px; background: #f8fafc; margin: 0; border-bottom: 1px solid #e2e8f0;">{{ date }}</h3>
                
                {% for city, leads in cities.items() %}
                <div style="border-left: 4px solid #dc2626; background: #fef2f2; margin: 10px 20px;">
                    <div style="padding: 10px 15px; font-weight: 600; color: #dc2626;">{{ city.title() }} ({{ leads|length }} leads)</div>
                    
                    <table class="leads-table">
                        <thead>
                            <tr>
                                <th>Permit #</th>
                                <th>Address</th>
                                <th>Type</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for lead in leads %}
                            <tr>
                                <td><span class="permit-number">{{ lead.permit_number }}</span></td>
                                <td><span class="address">{{ lead.address }}</span></td>
                                <td><span class="permit-type">{{ lead.type }}</span></td>
                                <td><span class="value">{{ lead.value }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% endfor %}
            </div>
            {% endfor %}
        </div>
        {% else %}
            <div class="no-data">
                <h3>No leads data found</h3>
                <p>Run a manual scrape or wait for the daily daemon to generate data.</p>
            </div>
        {% endif %}
    </div>
    
    <script>
        // Table sorting functionality
        console.log("Sorting script loaded!");
        
        function sortTable(table, column, asc = true) {
            console.log("sortTable called with column:", column, "asc:", asc);
            const dirModifier = asc ? 1 : -1;
            const tBody = table.tBodies[0];
            const rows = Array.from(tBody.querySelectorAll("tr"));
            
            console.log("Found", rows.length, "rows to sort");
            
            // Sort each row
            const sortedRows = rows.sort((a, b) => {
                const aColText = a.querySelector(`td:nth-child(${column + 1})`).textContent.trim();
                const bColText = b.querySelector(`td:nth-child(${column + 1})`).textContent.trim();
                
                // Try to parse as number for value column
                if (column === 3) { // Value column
                    const aVal = parseFloat(aColText.replace(/[$,]/g, '')) || 0;
                    const bVal = parseFloat(bColText.replace(/[$,]/g, '')) || 0;
                    return aVal > bVal ? dirModifier : aVal < bVal ? -dirModifier : 0;
                }
                
                // String comparison for other columns
                return aColText > bColText ? dirModifier : aColText < bColText ? -dirModifier : 0;
            });
            
            // Remove all existing TRs from tbody
            while (tBody.firstChild) {
                tBody.removeChild(tBody.firstChild);
            }
            
            // Re-add the newly sorted rows
            tBody.append(...sortedRows);
            
            // Remember how column is currently sorted
            table.querySelectorAll("th").forEach(th => th.classList.remove("sort-asc", "sort-desc"));
            table.querySelector(`th:nth-child(${column + 1})`).classList.toggle("sort-asc", asc);
            table.querySelector(`th:nth-child(${column + 1})`).classList.toggle("sort-desc", !asc);
        }
        
        // Add click handlers to all table headers
        document.querySelectorAll(".leads-table th").forEach(headerCell => {
            console.log("Adding click handler to header:", headerCell.textContent);
            headerCell.addEventListener("click", () => {
                console.log("Header clicked:", headerCell.textContent);
                const tableElement = headerCell.parentElement.parentElement.parentElement;
                const headerIndex = Array.prototype.indexOf.call(headerCell.parentElement.children, headerCell);
                const currentIsAscending = headerCell.classList.contains("sort-asc");
                
                console.log("Table element:", tableElement, "Header index:", headerIndex);
                sortTable(tableElement, headerIndex, !currentIsAscending);
            });
        });
        
        // Sort cities and states functionality
        document.querySelectorAll(".city-header").forEach(header => {
            console.log("Adding click handler to city header:", header.textContent);
            header.style.cursor = "pointer";
            header.style.userSelect = "none";
            header.addEventListener("click", () => {
                console.log("City header clicked:", header.textContent);
                const cityGrid = header.closest(".city-grid");
                const cityCards = Array.from(cityGrid.querySelectorAll(".city-card"));
                
                cityCards.sort((a, b) => {
                    const aText = a.querySelector(".city-header").textContent.trim();
                    const bText = b.querySelector(".city-header").textContent.trim();
                    return aText.localeCompare(bText);
                });
                
                // Reorder the cards
                cityCards.forEach(card => cityGrid.appendChild(card));
            });
        });
    </script>
</body>
</html>
'''

# === 1. STRIPE WEBHOOK ===
@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        data = event['data']['object']
        email = data['customer_details']['email']
        city = data['metadata']['city'].lower()
        
        # Save to Firestore
        doc_ref = db.collection('subscribers').document()
        doc_ref.set({
            'city': city,
            'email': email,
            'timestamp': datetime.datetime.now()
        })
        
        print(f"New subscriber: {email} for {city}")
        
        # Trigger scrape if city supported
        if city in CITIES:
            run_scraper(city)
        
    return '', 200

# === MANUAL SCRAPE ENDPOINT ===
@app.route('/manual_scrape', methods=['GET'])
def manual_scrape_endpoint():
    secret = request.args.get('secret')
    if secret != ADMIN_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    manual_scrape()
    return jsonify({"status": "Manual scrape completed"})

# === 2. CITY SCRAPER MANAGER ===
def run_scraper(city):
    try:
        if city == 'nashville':
            from scrapers import nashville
            permits = nashville.scrape_permits()
            nashville.save_to_csv(permits)
        elif city == 'chattanooga':
            from scrapers import chattanooga
            permits = chattanooga.scrape_permits()
            chattanooga.save_to_csv(permits)
        elif city == 'austin':
            from scrapers import austin
            permits = austin.scrape_permits()
            austin.save_to_csv(permits)
        elif city == 'sanantonio':
            from scrapers import sanantonio
            permits = sanantonio.scrape_permits()
            sanantonio.save_to_csv(permits)
        elif city == 'houston':
            from scrapers import houston
            permits = houston.scrape_permits()
            houston.save_to_csv(permits)
        elif city == 'charlotte':
            from scrapers import charlotte
            permits = charlotte.scrape_permits()
            charlotte.save_to_csv(permits)
        elif city == 'dallas':
            from scrapers import dallas
            permits = dallas.scrape_permits()
            dallas.save_to_csv(permits)
        elif city == 'raleigh':
            from scrapers import raleigh
            permits = raleigh.scrape_permits()
            raleigh.save_to_csv(permits)
        else:
            print(f'No scraper for {city}')
            return

        print(f'Scraped {len(permits)} permits for {city}')
    except Exception as e:
        print(f'Error scraping {city}: {e}')
        # Email alert on failure
        try:
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=[OWNER_EMAIL],
                subject=f'ALERT: {city} scrape FAILED at {time.ctime()}',
                plain_text_content=f'Site returned error. Fix ASAP. Error: {e}'
            )
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
        except Exception as email_error:
            print(f'Failed to send error email: {email_error}')

def manual_scrape():
    """Run all scrapers once manually"""
    for city in CITIES:
        run_scraper(city)
    print("Manual scrape completed. Check ../leads/ folder for today's data.")

# === 3. DAILY EMAIL & STORAGE ===
@app.route('/daily')
def send_daily():
    for city in CITIES:
        # Find yesterday's CSV
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        csv_path = f'../leads/{city}/{yesterday}/{yesterday}_{city}.csv'
        if os.path.exists(csv_path):
            # Get subscribers from Firestore
            subscribers_ref = db.collection('subscribers').where('city', '==', city)
            docs = subscribers_ref.stream()
            
            # Read CSV
            df = pd.read_csv(csv_path)
            leads_data = df.to_dict('records')
            
            for doc in docs:
                subscriber = doc.to_dict()
                email = subscriber['email']
                
                # Store leads for this subscriber
                leads_ref = db.collection('user_leads').document(email).collection('leads')
                for lead in leads_data:
                    lead_doc = {
                        'city': city,
                        'date': yesterday,
                        'permit_number': lead.get('permit_number', ''),
                        'address': lead.get('address', ''),
                        'type': lead.get('type', ''),
                        'value': lead.get('value', ''),
                        'created_at': datetime.datetime.now()
                    }
                    # Use permit number + city + date as unique ID
                    doc_id = f"{lead.get('permit_number', 'unknown')}_{city}_{yesterday}".replace('/', '_')
                    leads_ref.document(doc_id).set(lead_doc)
                
                # Send email
                html_table = df.to_html(index=False)
                message = Mail(
                    from_email=FROM_EMAIL,
                    to_emails=[email],
                    subject=f'{city.capitalize()} Permits - {datetime.date.today()}',
                    html_content=f'<h2>Yesterday\'s leads for {city}:</h2>{html_table}'
                )
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                sg.send(message)
    
    return 'Sent and stored', 200

# === 4. AUTHENTICATION ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Check if email exists in subscribers
            subscribers_ref = db.collection('subscribers').where('email', '==', email)
            docs = subscribers_ref.stream()
            if len(list(docs)) > 0:
                # Create session (simple cookie-based)
                response = make_response(redirect('/dashboard'))
                response.set_cookie('user_email', email, max_age=30*24*3600)  # 30 days
                return response
            else:
                return render_template_string(LOGIN_TEMPLATE, error="Email not found in subscribers")
        return render_template_string(LOGIN_TEMPLATE, error="Please enter an email")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('user_email')
    return response

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Check if email already exists
            subscribers_ref = db.collection('subscribers').where('email', '==', email)
            docs = subscribers_ref.stream()
            if len(list(docs)) > 0:
                return render_template_string(SIGNUP_TEMPLATE, error="Email already registered")
            else:
                # For now, just add to a mailing list collection
                mailing_ref = db.collection('mailing_list').document()
                mailing_ref.set({
                    'email': email,
                    'timestamp': datetime.datetime.now()
                })
                return render_template_string(SIGNUP_TEMPLATE, success="Thanks! We'll notify you when new cities are added.")
        return render_template_string(SIGNUP_TEMPLATE, error="Please enter an email")
    
    return render_template_string(SIGNUP_TEMPLATE)

# === 5. DASHBOARD ===
@app.route('/dashboard')
def dashboard():
    email = request.cookies.get('user_email')
    if not email:
        return redirect('/login')
    
    # Get user's cities
    subscribers_ref = db.collection('subscribers').where('email', '==', email)
    docs = subscribers_ref.stream()
    user_cities = [doc.to_dict()['city'] for doc in docs]
    
    # Get leads grouped by date and city
    leads_ref = db.collection('user_leads').document(email).collection('leads')
    leads_docs = leads_ref.order_by('date', direction=firestore.Query.DESCENDING).stream()
    
    leads_by_date = {}
    for doc in leads_docs:
        lead = doc.to_dict()
        date = lead['date']
        city = lead['city']
        if date not in leads_by_date:
            leads_by_date[date] = {}
        if city not in leads_by_date[date]:
            leads_by_date[date][city] = []
        leads_by_date[date][city].append(lead)
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                email=email, 
                                user_cities=user_cities, 
                                leads_by_date=leads_by_date)

# === ADMIN DASHBOARD ===
@app.route('/admin')
def admin_dashboard():
    # Handle logout
    if request.args.get('logout'):
        response = make_response(redirect('/admin'))
        response.delete_cookie('admin_secret')
        return response
    
    # Check admin authentication via cookie or query param
    admin_secret = request.cookies.get('admin_secret') or request.args.get('secret')
    if admin_secret != ADMIN_SECRET:
        return render_template_string(ADMIN_LOGIN_TEMPLATE)
    
    # Get all CSV files from all cities
    all_leads = {}
    total_leads = 0
    cities_data = {}
    
    for city in CITIES:
        city_path = f'../leads/{city}'
        if os.path.exists(city_path):
            # Look for all date directories
            date_dirs = [d for d in os.listdir(city_path) if os.path.isdir(os.path.join(city_path, d)) and d.startswith('2025-')]
            csv_files = []
            for date_dir in sorted(date_dirs, reverse=True):
                dir_path = os.path.join(city_path, date_dir)
                dir_files = [os.path.join(date_dir, f) for f in os.listdir(dir_path) if f.endswith('.csv')]
                csv_files.extend(dir_files)
            cities_data[city] = {'files': csv_files, 'leads': []}
            
            for csv_file in sorted(csv_files, reverse=True):  # Most recent first
                file_path = os.path.join(city_path, csv_file)
                try:
                    df = pd.read_csv(file_path)
                    leads = df.to_dict('records')
                    cities_data[city]['leads'].extend(leads)
                    total_leads += len(leads)
                    
                    # Group by date
                    date = csv_file.split('/')[0]  # Extract date from directory name
                    if date not in all_leads:
                        all_leads[date] = {}
                    all_leads[date][city] = leads
                    
                except Exception as e:
                    print(f'Error reading {file_path}: {e}')
    
    # Get recent activity (last 7 days)
    recent_dates = []
    for i in range(7):
        date = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        recent_dates.append(date)
    
    recent_activity = {date: all_leads.get(date, {}) for date in recent_dates}
    
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
                                cities_data=cities_data,
                                all_leads=all_leads,
                                total_leads=total_leads,
                                recent_activity=recent_activity,
                                cities=CITIES)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    secret = request.form.get('secret')
    if secret == ADMIN_SECRET:
        response = make_response(redirect('/admin'))
        response.set_cookie('admin_secret', ADMIN_SECRET, max_age=24*3600)  # 24 hours
        return response
    return render_template_string(ADMIN_LOGIN_TEMPLATE, error="Invalid admin secret")

# === 6. FRONTEND SERVE ===
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# === 5. DAILY SCRAPER SCHEDULER ===
def scheduled_scrape_daily():
    """Run all scrapers daily at 2:30 PM CST"""
    import time

    while True:
        # Get current time
        now = time.localtime()
        current_hour = now.tm_hour
        current_min = now.tm_min

        # Calculate target time: 2:30 PM (14:30)
        target_hour = 14  # 2 PM
        target_min = 30   # 30 minutes

        # Calculate seconds until target time
        current_seconds = current_hour * 3600 + current_min * 60
        target_seconds = target_hour * 3600 + target_min * 60

        if current_seconds < target_seconds:
            # Target time is later today
            seconds_to_wait = target_seconds - current_seconds
        else:
            # Target time has already passed today, wait until tomorrow
            seconds_to_wait = (24 * 3600) - current_seconds + target_seconds

        print(f"Scheduling daily scrape for 2:30 PM CST (in {seconds_to_wait} seconds)")
        time.sleep(seconds_to_wait)

        print("🕐 Running daily scheduled scrape at 2:30 PM CST...")
        manual_scrape()
        print("✅ Daily scheduled scrape completed!")

        # Wait until next day (this will be interrupted by the sleep above for next day)
        time.sleep(60)  # Check every minute

# === 5. RANDOM MORNING SCRAPER DAEMON ===
def random_morning_scrape():
    while True:
        now = time.localtime()
        if 5 <= now.tm_hour < 6:
            # Sleep random seconds between 0 and 1800 (30 minutes) for no pattern
            target_sec = random.randint(0, 1800)
            time.sleep(target_sec)
            
            for city in CITIES:
                run_scraper(city)
            
            # Sleep until next day 5 AM
            time.sleep(24 * 3600 - (time.time() % (24 * 3600)) + 5 * 3600)
        else:
            time.sleep(60)  # Check every minute

# === RUN ===
if __name__ == '__main__':
    import sys
    
    # Check for manual scrape command
    if len(sys.argv) > 1 and sys.argv[1].startswith('--city='):
        city = sys.argv[1].split('=')[1]
        print(f"🔧 Manual scrape for {city}")
        run_scraper(city)
        print(f"✅ Manual scrape completed for {city}")
        sys.exit(0)
    
    print("🚀 Server starting...")
    # Run server (no debug/watchdog for testing)
    app.run(port=8080)