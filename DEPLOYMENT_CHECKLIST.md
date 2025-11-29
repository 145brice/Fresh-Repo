# Deployment Checklist

## Pre-Deployment

### 1. Stripe Setup (Test Mode)
- [ ] Create Nashville product ($47/month)
  - Price ID: `price_________________`
- [ ] Create Chattanooga product ($47/month)
  - Price ID: `price_________________`
- [ ] Create Austin product ($47/month)
  - Price ID: `price_________________`
- [ ] Create San Antonio product ($47/month)
  - Price ID: `price_________________`
- [ ] Create Houston product ($47/month)
  - Price ID: `price_________________`
- [ ] Create Charlotte product ($47/month)
  - Price ID: `price_________________`
- [ ] Create Phoenix product ($47/month)
  - Price ID: `price_________________`
- [ ] Create All Cities Bundle product ($97/month)
  - Price ID: `price_________________`
- [ ] Copy Stripe Secret Key: `sk_test_________________`

### 2. Firebase Setup
- [ ] Create Firebase project
- [ ] Enable Firestore Database
- [ ] Download service account JSON
- [ ] Extract all credentials:
  - [ ] project_id
  - [ ] private_key_id
  - [ ] private_key (with \n)
  - [ ] client_email
  - [ ] client_id
  - [ ] cert_url

### 3. SendGrid Setup
- [ ] Create SendGrid account
- [ ] Create API key (Full Access)
- [ ] Verify sender email
- [ ] Copy API key: `SG.________________`
- [ ] Note verified email: `________________`

## Backend Deployment (Railway)

- [ ] Push code to GitHub
- [ ] Create Railway project
- [ ] Connect GitHub repo
- [ ] Add all environment variables:
  - [ ] STRIPE_SECRET_KEY
  - [ ] FRONTEND_URL (add after Netlify deploy)
  - [ ] FIREBASE_PROJECT_ID
  - [ ] FIREBASE_PRIVATE_KEY_ID
  - [ ] FIREBASE_PRIVATE_KEY
  - [ ] FIREBASE_CLIENT_EMAIL
  - [ ] FIREBASE_CLIENT_ID
  - [ ] FIREBASE_CERT_URL
  - [ ] SENDGRID_API_KEY
  - [ ] FROM_EMAIL
  - [ ] OWNER_EMAIL
  - [ ] ADMIN_SECRET
- [ ] Deploy and copy Railway URL: `https://________________`

## Stripe Webhook Setup

- [ ] Go to Stripe Webhooks
- [ ] Add endpoint: `https://[your-railway-url]/webhook`
- [ ] Select events:
  - [ ] checkout.session.completed
  - [ ] invoice.payment_failed
  - [ ] customer.subscription.deleted
- [ ] Copy webhook secret: `whsec_________________`
- [ ] Add to Railway: STRIPE_WEBHOOK_SECRET

## Frontend Deployment (Netlify)

- [ ] Update frontend/index.html:
  - [ ] Replace all 4 price IDs in STRIPE_PRICE_IDS object
  - [ ] Replace BACKEND_URL with Railway URL
- [ ] Deploy to Netlify (drag & drop frontend folder)
- [ ] Copy Netlify URL: `https://________________`
- [ ] Update Railway FRONTEND_URL variable

## Testing

- [ ] Visit Netlify URL
- [ ] Click Nashville button
- [ ] Complete checkout with test card: 4242 4242 4242 4242
- [ ] Verify redirects to success page
- [ ] Check Firebase for new subscriber document
- [ ] Verify Stripe webhook received in dashboard
- [ ] Test manual email send:
  ```bash
  curl -X POST https://your-railway-url/manual-send \
    -H "Authorization: Bearer your-admin-secret"
  ```
- [ ] Check email received at subscriber address
- [ ] Check owner email for master CSV

## Go Live

- [ ] Switch Stripe to Live mode
- [ ] Create 4 new products in Live mode
- [ ] Update price IDs in frontend
- [ ] Update Railway with live Stripe keys
- [ ] Create new webhook in live mode
- [ ] Update Railway with live webhook secret
- [ ] Test with real card (your own)
- [ ] Monitor for 24 hours

## Post-Launch

- [ ] Set up daily reminder to check Railway logs at 8 AM
- [ ] Verify first automated email delivery
- [ ] Save all credentials in password manager
- [ ] Document any custom lead sources
- [ ] Set calendar reminder to check subscriber count weekly

## Emergency Contacts

- Railway Support: https://railway.app/help
- Stripe Support: https://support.stripe.com/
- SendGrid Support: https://support.sendgrid.com/
- Netlify Support: https://www.netlify.com/support/

## Quick Links

- Stripe Dashboard: https://dashboard.stripe.com/
- Firebase Console: https://console.firebase.google.com/
- SendGrid Dashboard: https://app.sendgrid.com/
- Railway Dashboard: https://railway.app/dashboard
- Netlify Dashboard: https://app.netlify.com/

---

**Remember:** 
- Users manage subscriptions through Stripe (no customer support needed)
- Daily emails go out at 8 AM Central automatically
- You get master CSV every morning
- Check Railway logs if emails don't send
