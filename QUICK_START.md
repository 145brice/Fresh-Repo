# 🚀 Quick Start - Get Live in 30 Minutes

This is your express guide to getting the contractor leads SaaS live. Follow these steps in order.

## ⏱️ Timeline
- Setup (15 min): Stripe, Firebase, SendGrid accounts
- Deploy Backend (5 min): Railway
- Deploy Frontend (5 min): Netlify
- Test (5 min): End-to-end checkout

---

## 📋 Before You Start

Have these open in browser tabs:
1. https://dashboard.stripe.com/test/products
2. https://console.firebase.google.com/
3. https://app.sendgrid.com/
4. https://railway.app/
5. https://app.netlify.com/

---

## Step 1: Stripe (5 min)

1. **Create 8 Products** at https://dashboard.stripe.com/test/products
   - Click "Add product"
   - Name: "Nashville Contractor Leads"
   - Price: $47.00
   - Billing period: Monthly
   - Click "Add product"
   - **Copy the Price ID** (starts with `price_`)
   
   Repeat for Chattanooga ($47), Austin ($47), San Antonio ($47), Houston ($47), Charlotte ($47), Phoenix ($47), and "All Cities Bundle" ($97)

2. **Get your Secret Key**
   - Go to https://dashboard.stripe.com/test/apikeys
   - Copy "Secret key" (starts with `sk_test_`)

3. **Save these for later:**
   ```
   NASHVILLE_PRICE_ID: price_________________
   CHATTANOOGA_PRICE_ID: price_________________
   AUSTIN_PRICE_ID: price_________________
   SANANTONIO_PRICE_ID: price_________________
   STRIPE_SECRET_KEY: sk_test_________________
   ```

---

## Step 2: Firebase (5 min)

1. **Create Project** at https://console.firebase.google.com/
   - Click "Add project"
   - Name it: "contractor-leads"
   - Disable Google Analytics (not needed)
   - Click "Create project"

2. **Enable Firestore**
   - Left sidebar → Firestore Database
   - Click "Create database"
   - Start in production mode
   - Choose your region (us-central1)
   - Click "Enable"

3. **Get Service Account**
   - Click gear icon (top left) → Project settings
   - Click "Service accounts" tab
   - Click "Generate new private key"
   - Click "Generate key"
   - JSON file downloads
   - **Open it and copy these values:**
   ```
   FIREBASE_PROJECT_ID: ________________
   FIREBASE_PRIVATE_KEY_ID: ________________
   FIREBASE_PRIVATE_KEY: -----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n
   FIREBASE_CLIENT_EMAIL: ________________
   FIREBASE_CLIENT_ID: ________________
   FIREBASE_CERT_URL: ________________
   ```

---

## Step 3: SendGrid (3 min)

1. **Create Account** at https://signup.sendgrid.com/
   - Use free tier (40,000 emails/month for 30 days, then 100/day)

2. **Create API Key**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: "contractor-leads"
   - Permissions: "Full Access"
   - Click "Create & View"
   - **Copy the key** (starts with `SG.`)
   ```
   SENDGRID_API_KEY: SG.________________
   ```

3. **Verify Sender Email**
   - Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Fill in your email
   - Check your email and click verify link
   ```
   FROM_EMAIL: your-verified@email.com
   OWNER_EMAIL: your@email.com
   ```

---

## Step 4: Deploy Backend to Railway (5 min)

1. **Push to GitHub First**
   ```bash
   cd contractor-leads-saas
   git init
   git add .
   git commit -m "Initial commit"
   gh repo create contractor-leads-backend --private --source=. --push
   ```

2. **Deploy to Railway**
   - Go to https://railway.app/new
   - Click "Deploy from GitHub repo"
   - Select your repo
   - Railway auto-detects Python
   - Click "Deploy"

3. **Add Environment Variables**
   - Click on your deployment
   - Click "Variables" tab
   - Click "New Variable"
   - Add all these (paste your actual values):
   
   ```
   STRIPE_SECRET_KEY=sk_test_your_key
   STRIPE_WEBHOOK_SECRET=whsec_we_will_add_this_next
   FRONTEND_URL=https://we-will-add-this-after-netlify
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_PRIVATE_KEY_ID=your-key-id
   FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nyour-key\n-----END PRIVATE KEY-----\n
   FIREBASE_CLIENT_EMAIL=your-email@project.iam.gserviceaccount.com
   FIREBASE_CLIENT_ID=your-client-id
   FIREBASE_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-url
   SENDGRID_API_KEY=SG.your-key
   FROM_EMAIL=your-verified@email.com
   OWNER_EMAIL=your@email.com
   ADMIN_SECRET=test123
   PORT=5000
   ```

4. **Copy Railway URL**
   - After deployment, click "Deployments" tab
   - Copy the domain (e.g., `contractor-leads-production.up.railway.app`)
   ```
   RAILWAY_URL: https://________________.railway.app
   ```

---

## Step 5: Setup Stripe Webhook (2 min)

1. **Add Webhook Endpoint**
   - Go to https://dashboard.stripe.com/test/webhooks
   - Click "Add endpoint"
   - Endpoint URL: `https://your-railway-url.railway.app/webhook`
   - Click "Select events"
   - Search and select:
     - checkout.session.completed
     - invoice.payment_failed
     - customer.subscription.deleted
   - Click "Add events"
   - Click "Add endpoint"

2. **Copy Webhook Secret**
   - Click on your new endpoint
   - Click "Reveal" under "Signing secret"
   - Copy it (starts with `whsec_`)
   ```
   STRIPE_WEBHOOK_SECRET: whsec_________________
   ```

3. **Update Railway**
   - Go back to Railway
   - Variables tab
   - Update `STRIPE_WEBHOOK_SECRET` with the real value
   - App will auto-redeploy

---

## Step 6: Deploy Frontend to Netlify (5 min)

1. **Update Frontend Files First**
   
   Edit `frontend/index.html`:
   - Line 75-80: Replace with YOUR price IDs:
   ```javascript
   const STRIPE_PRICE_IDS = {
       'nashville': 'price_YOUR_NASHVILLE_ID',
       'chattanooga': 'price_YOUR_CHATTANOOGA_ID',
       'austin': 'price_YOUR_AUSTIN_ID',
       'san-antonio': 'price_YOUR_SANANTONIO_ID'
   };
   ```
   
   - Line 83: Replace with YOUR Railway URL:
   ```javascript
   const BACKEND_URL = 'https://your-railway-url.railway.app';
   ```

2. **Deploy to Netlify**
   - Go to https://app.netlify.com/drop
   - Drag and drop the entire `frontend` folder
   - Wait 10 seconds
   - Site is live!

3. **Copy Netlify URL**
   ```
   NETLIFY_URL: https://________________.netlify.app
   ```

4. **Update Railway**
   - Go back to Railway → Variables
   - Update `FRONTEND_URL` with your Netlify URL
   - App will auto-redeploy

---

## Step 7: Test Everything (5 min)

### Test Checkout
1. Go to your Netlify URL
2. Click "Nashville" button
3. Use test card: `4242 4242 4242 4242`
4. Any future expiry (e.g., 12/34)
5. Any CVC (e.g., 123)
6. Any ZIP (e.g., 12345)
7. Click "Subscribe"
8. Should redirect to success page ✅

### Verify Database
1. Go to Firebase Console → Firestore
2. Click "subscribers" collection
3. Should see one document with your test email ✅

### Test Email
```bash
curl -X POST https://your-railway-url.railway.app/manual-send \
  -H "Authorization: Bearer test123"
```

Check both emails:
- Test subscriber email: Should get HTML table with leads ✅
- Your owner email: Should get CSV attachment ✅

---

## ✅ You're Live!

Your SaaS is now running:
- ✅ Payments work
- ✅ Database saving subscribers
- ✅ Emails sending
- ✅ Daily cron will run at 8 AM Central

---

## What Happens Next?

1. **Tomorrow at 8 AM Central:**
   - All active subscribers get their daily leads email
   - You get a master CSV with all subscribers

2. **When Someone Subscribes:**
   - They pay through Stripe
   - Webhook saves them to Firebase with `active: true`
   - They start receiving daily emails tomorrow

3. **When Someone Cancels:**
   - They click manage subscription in Stripe receipt
   - Cancel themselves
   - Webhook sets `active: false`
   - Emails stop immediately

---

## 🐛 Quick Troubleshooting

**Webhook not working?**
- Check Railway logs: Click deployment → Logs
- Verify webhook secret in Railway matches Stripe
- Check Stripe webhook dashboard for delivery attempts

**Email not sending?**
- Verify sender email in SendGrid
- Check SendGrid activity feed
- Ensure API key has full access

**Can't checkout?**
- Check browser console for errors
- Verify price IDs are correct in frontend
- Check Railway URL is correct in frontend

---

## 📞 Get Help

- Check `API_REFERENCE.md` for endpoint details
- Check `README.md` for comprehensive guide
- Check Railway logs for server errors
- Check Stripe webhook dashboard for webhook errors

---

## 🚀 Ready to Go Live?

See `DEPLOYMENT_CHECKLIST.md` for the full live deployment process.

**Main changes for live:**
1. Create new Stripe products in Live mode
2. Update Railway with live Stripe keys
3. Create new webhook in Stripe Live mode
4. Update frontend with live price IDs
5. Test with your own real card

**That's it! You're running a real SaaS.**
