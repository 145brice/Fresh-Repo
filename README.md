# Contractor Leads Backend

Backend API for the Contractor Leads SaaS platform. This service handles permit data scraping, user management, and email distribution.

## Features

- **Permit Scraping**: Automated daily scraping from multiple city data sources
- **User Management**: Firebase/Firestore integration for subscribers
- **Email Distribution**: Daily leads via SendGrid
- **Admin Dashboard**: Web interface for monitoring and data management
- **Stripe Integration**: Payment processing for subscriptions

## Supported Cities

Currently working cities:
- Austin, TX
- Dallas, TX  
- Raleigh, NC
- Chattanooga, TN
- Nashville, TN

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export STRIPE_SECRET_KEY="your_stripe_key"
export STRIPE_WEBHOOK_SECRET="your_webhook_secret"
export SENDGRID_API_KEY="your_sendgrid_key"
export RESEND_API_KEY="your_resend_key"
export OWNER_EMAIL="your@email.com"
export FROM_EMAIL="leads@yourdomain.com"
export ADMIN_SECRET="your_admin_secret"
```

3. Run the server:
```bash
python backend.py
```

The server will start on port 8080.

## API Endpoints

- `GET /admin?secret=admin123` - Admin dashboard
- `POST /webhook` - Stripe webhook handler
- `GET /manual_scrape?secret=admin123` - Manual scrape trigger
- `POST /signup` - User signup
- `POST /login` - User login

## Architecture

- **Flask**: Web framework
- **Firebase/Firestore**: Database
- **Stripe**: Payments
- **SendGrid**: Email delivery
- **BeautifulSoup/Requests**: Web scraping

## Deployment

This backend can be deployed to any Python-compatible hosting service (Heroku, DigitalOcean, AWS, etc.).

For production, set up proper environment variables and consider using a WSGI server like Gunicorn.
