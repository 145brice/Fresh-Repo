# Contractor Leads SaaS - Deployment Guide

Dead simple contractor leads platform. Seven cities, $47/month each or $97 for all cities bundle, daily email delivery.

## Project Structure
```
contractor-leads-saas/
├── frontend/
│   ├── index.html          # Landing page with 7 city buttons + bundle
│   └── success.html        # Post-checkout success page
├── backend/
│   ├── app.py             # Flask app with webhook + cron
│   ├── requirements.txt   # Python dependencies
│   └── railway.json       # Railway config
├── .gitignore
└── README.md
```

## Prerequisites

1. **Stripe Account** (test mode)
2. **Firebase Project** (free tier)
3. **SendGrid Account** (free tier)
4. **Railway Account** (or Render)
5. **Netlify Account** (for frontend)

---

## Step 1: Create Stripe Products

1. Go to https://dashboard.stripe.com/test/products
2. Create 8 products:
   - **Nashville Contractor Leads** - $47/month recurring
   - **Chattanooga Contractor Leads** - $47/month recurring
   - **Austin Contractor Leads** - $47/month recurring
   - **San Antonio Contractor Leads** - $47/month recurring
   - **Houston Contractor Leads** - $47/month recurring
   - **Charlotte Contractor Leads** - $47/month recurring
   - **Phoenix Contractor Leads** - $47/month recurring
   - **All Cities Bundle** - $97/month recurring

3. Copy each **Price ID** (starts with `price_`)

4. Get your keys:
   - Secret key: https://dashboard.stripe.com/test/apikeys
   - Webhook secret: (we'll get this in Step 4)

---

## Step 2: Setup Firebase

1. Go to https://console.firebase.google.com/
2. Create new project (or use existing)
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Download the JSON file
6. You'll need these values from the JSON:
   - `project_id`
   - `private_key_id`
   - `private_key`
   - `client_email`
   - `client_id`
   - `client_x509_cert_url`

7. Enable Firestore:
   - Go to **Firestore Database**
   - Click **Create Database**
   - Start in **Production mode**
   - Choose your region

---

## Step 3: Setup SendGrid

1. Go to https://app.sendgrid.com/
2. Create account (free tier is fine)
3. Go to **Settings** → **API Keys**
4. Create new API key with **Full Access**
5. Copy the key (you won't see it again)
6. Verify a sender email:
   - Go to **Settings** → **Sender Authentication**
   - Verify your email address (this will be your FROM_EMAIL)

---

## Step 4: Deploy Backend to Railway

1. Go to https://railway.app/
2. Create new project → **Deploy from GitHub**
3. Connect your GitHub repo (push backend folder first)
4. Railway will auto-detect Python and deploy

5. Add environment variables in Railway dashboard:

```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...   # Get this in next step
FRONTEND_URL=https://your-site.netlify.app

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=...
FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@...iam.gserviceaccount.com
FIREBASE_CLIENT_ID=...
FIREBASE_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# SendGrid
SENDGRID_API_KEY=SG....
FROM_EMAIL=you@yourdomain.com
OWNER_EMAIL=you@yourdomain.com

# Optional
ADMIN_SECRET=your-secret-for-manual-testing
PORT=5000
```

6. Deploy and copy your Railway URL (e.g., `https://contractor-leads-production.up.railway.app`)

---

## Step 5: Configure Stripe Webhook

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click **Add endpoint**
3. Endpoint URL: `https://your-railway-url.railway.app/webhook`
4. Select events to listen to:
   - `checkout.session.completed`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
5. Add endpoint
6. Copy the **Signing secret** (starts with `whsec_`)
7. Add it to Railway as `STRIPE_WEBHOOK_SECRET`

---

## Step 6: Deploy Frontend to Netlify

1. Go to https://app.netlify.com/
2. Drag and drop the `frontend` folder
3. Site will deploy instantly

4. **Update frontend/index.html:**
   - Replace `STRIPE_PRICE_IDS` with your actual price IDs
   - Replace `BACKEND_URL` with your Railway URL

5. Re-upload to Netlify (or connect to Git for auto-deploy)

6. Copy your Netlify URL

7. **Update Railway:**
   - Add `FRONTEND_URL` env var with your Netlify URL

---

## Step 7: Test Everything

### Test Stripe Checkout
1. Go to your Netlify URL
2. Click any city button
3. Use test card: `4242 4242 4242 4242`
4. Any future date, any CVC
5. Should redirect to success page

### Verify Database
1. Go to Firebase Console → Firestore
2. Check `subscribers` collection
3. Should see new document with customer email and city

### Test Daily Email (Manual)
```bash
curl -X POST https://your-railway-url.railway.app/manual-send \
  -H "Authorization: Bearer your-secret"
```

Check your owner email and the test subscriber's email.

---

## How It Works

### User Flow
1. User clicks city button → Stripe Checkout
2. Pays $47/month → Webhook fires
3. Backend saves to Firebase with `active: true`
4. User gets receipt email from Stripe

### Daily Cron (8 AM Central)
1. Backend pulls all `active: true` subscribers
2. Groups by city
3. Sends each subscriber their city's leads
4. Emails you a master CSV with all active subscribers

### Cancellation
- User clicks manage subscription link in Stripe receipt
- Cancels themselves
- Webhook fires → sets `active: false`
- No more emails

---

## Environment Variables Reference

### Required
```bash
STRIPE_SECRET_KEY          # sk_test_... or sk_live_...
STRIPE_WEBHOOK_SECRET      # whsec_...
SENDGRID_API_KEY          # SG...
FROM_EMAIL                # verified sender
OWNER_EMAIL               # where you get daily report
FRONTEND_URL              # your Netlify URL
```

### Firebase (all required)
```bash
FIREBASE_PROJECT_ID
FIREBASE_PRIVATE_KEY_ID
FIREBASE_PRIVATE_KEY       # Include \n characters
FIREBASE_CLIENT_EMAIL
FIREBASE_CLIENT_ID
FIREBASE_CERT_URL
```

---

## Going Live

1. **Switch Stripe to Live Mode:**
   - Create new products in live mode
   - Get new price IDs
   - Update frontend with live price IDs
   - Get new webhook secret
   - Update Railway env vars with live keys

2. **Test with real card (yours)**

3. **Update pricing/cities as needed**

---

## Maintenance

- **Add more cities:** Create new Stripe product, add button to frontend
- **Change price:** Create new price in Stripe, update frontend
- **View subscribers:** Check Firebase Console or wait for daily CSV
- **Manual test email:** Hit `/manual-send` endpoint

---

## Troubleshooting

**Webhook not working:**
- Check Railway logs: `railway logs`
- Verify webhook secret matches Stripe
- Check Stripe webhook dashboard for errors

**Emails not sending:**
- Verify SendGrid sender email
- Check SendGrid activity feed
- Verify SENDGRID_API_KEY has full access

**Daily cron not running:**
- Railway automatically runs the scheduler
- Check logs at 8 AM Central
- Test with `/manual-send`

**Firebase errors:**
- Double-check all env vars copied correctly
- Ensure private_key has \n characters intact
- Verify Firestore is enabled

---

## Support

No customer support needed - users manage everything through Stripe:
- Billing questions → Stripe receipt
- Cancel → Stripe receipt link
- Update card → Stripe customer portal

You just send leads every morning. That's it.

---

## Quick Deploy Checklist

- [ ] Create 4 Stripe products with price IDs
- [ ] Setup Firebase project and download credentials
- [ ] Create SendGrid account and verify sender
- [ ] Deploy backend to Railway with all env vars
- [ ] Setup Stripe webhook pointing to Railway URL
- [ ] Update frontend with price IDs and backend URL
- [ ] Deploy frontend to Netlify
- [ ] Test subscription flow end-to-end
- [ ] Test manual email send
- [ ] Switch to live mode when ready

Done! 🚀
