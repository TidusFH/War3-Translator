# Google Translate API Setup Guide

This guide explains how to set up Google Translate API for the War3 Translator tool. You have **two options**: use the free version (no API key) or the official Google Cloud API (with API key for better performance).

## 🆓 Option 1: Free Version (No API Key) - CURRENT DEFAULT

### Setup

```bash
pip install googletrans==4.0.0rc1
python translator2.py
```

### Pros
✅ Completely free
✅ No setup required
✅ No Google account needed
✅ Works immediately

### Cons
⚠️ Rate limiting (slower for large campaigns)
⚠️ Less reliable (may occasionally fail)
⚠️ No official support

### When to Use
- Personal/hobby projects
- Small campaigns (< 10 maps)
- Testing the tool
- No budget for API costs

---

## 🔑 Option 2: Official Google Cloud API (With API Key) - RECOMMENDED

### Pros
✅ Higher rate limits (1000+ translations/min)
✅ More reliable
✅ Official Google support
✅ Better translation quality
✅ Detailed usage analytics

### Cons
⚠️ Requires Google Cloud account
⚠️ Costs money (but has free tier: $10/month credit)
⚠️ Setup required

### When to Use
- Professional/commercial projects
- Large campaigns (10+ maps)
- Batch processing multiple campaigns
- Need reliability and speed

---

## 📝 Setup Instructions for Official API

### Step 1: Create a Google Cloud Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account (or create one)
3. Accept the terms of service

### Step 2: Create a New Project

1. Click the **project dropdown** at the top (or go to [Create Project](https://console.cloud.google.com/projectcreate))
2. Click **"New Project"**
3. Enter project name: `Warcraft-Translator` (or any name you like)
4. Click **"Create"**
5. Wait for project creation (takes ~30 seconds)
6. Select your new project from the dropdown

### Step 3: Enable the Translation API

1. Go to [Translation API page](https://console.cloud.google.com/apis/library/translate.googleapis.com)
2. Click **"Enable"** button
3. Wait for API to be enabled (~1 minute)

### Step 4: Set Up Billing (Required, but has FREE TIER)

**Don't worry!** Google provides:
- **$300 free credit** for new accounts (90 days)
- **$10/month ongoing credit** for Translation API
- You only pay if you exceed the free tier

1. Go to [Billing](https://console.cloud.google.com/billing)
2. Click **"Link a billing account"** or **"Create billing account"**
3. Enter your payment information (credit/debit card)
4. Complete the setup

**Free Tier Details:**
- First **500,000 characters per month = FREE**
- After that: **$20 per million characters**
- Example: A typical campaign with 5,000 strings ≈ 100,000 characters = **FREE**

### Step 5: Create API Credentials

Choose **ONE** of the following methods:

#### Method A: API Key (Simpler, less secure)

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"API key"**
4. Copy your API key (looks like: `AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
5. Click **"RESTRICT KEY"** (recommended)
   - Under "API restrictions", select **"Restrict key"**
   - Choose **"Cloud Translation API"**
   - Click **"Save"**

#### Method B: Service Account (More secure, recommended for production)

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **"+ CREATE CREDENTIALS"**
3. Select **"Service account"**
4. Enter service account name: `warcraft-translator`
5. Click **"Create and Continue"**
6. For role, select **"Cloud Translation API User"**
7. Click **"Continue"** then **"Done"**
8. Click on the service account you just created
9. Go to **"Keys"** tab
10. Click **"Add Key" > "Create new key"**
11. Choose **"JSON"** format
12. Click **"Create"**
13. Save the downloaded `.json` file securely

### Step 6: Configure the War3 Translator

#### For Method A (API Key):

1. Copy `config.ini.template` to `config.ini`:
   ```bash
   copy config.ini.template config.ini
   ```

2. Open `config.ini` in a text editor

3. Uncomment and add your API key:
   ```ini
   [GoogleTranslate]
   api_key = AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. Save the file

#### For Method B (Service Account JSON):

1. Copy `config.ini.template` to `config.ini`:
   ```bash
   copy config.ini.template config.ini
   ```

2. Open `config.ini` in a text editor

3. Uncomment and add your credentials path:
   ```ini
   [GoogleTranslate]
   credentials_path = C:\Users\YourName\Downloads\warcraft-translator-12345.json
   ```

4. Save the file

### Step 7: Install the Official API Library

Uncomment the line in `requirements.txt`:

```txt
google-cloud-translate>=3.0.0
```

Then install:

```bash
pip install google-cloud-translate
```

Or install directly:

```bash
pip install google-cloud-translate>=3.0.0
```

### Step 8: Test Your Setup

Run the translator:

```bash
python translator2.py
```

When you select Mode 5 (campaign), you should see:

```
✓ Using Google Cloud Translation API (Official)
```

If it says this, you're all set! 🎉

---

## 🔒 Security Best Practices

### Protect Your API Key

1. **Never commit config.ini to GitHub**
   - Already included in `.gitignore`
   - Don't share your config.ini file

2. **Keep credentials JSON safe**
   - Store in a secure location
   - Don't commit to version control
   - Don't share publicly

3. **Restrict your API key** (if using Method A)
   - Limit to Translation API only
   - Set application restrictions if possible
   - Regenerate if compromised

### Set Up Budget Alerts (Recommended)

1. Go to [Billing > Budgets & alerts](https://console.cloud.google.com/billing/budgets)
2. Click **"CREATE BUDGET"**
3. Set a budget amount (e.g., $5)
4. Set alerts at 50%, 90%, 100%
5. Add your email for notifications

This way you'll be notified if costs exceed expectations!

---

## 💰 Cost Examples

Based on Google Cloud Translation API pricing:

| Campaign Size | Character Count | Cost (USD) |
|--------------|----------------|------------|
| Small (1-3 maps) | 50,000 chars | **$0.00** (free tier) |
| Medium (4-10 maps) | 200,000 chars | **$0.00** (free tier) |
| Large (11-20 maps) | 600,000 chars | **~$2.00** |
| Very Large (20+ maps) | 1,000,000 chars | **~$10.00** |

**Note:** First 500,000 characters per month are free!

---

## 🔄 Switching Between Free and Official API

The tool automatically detects which version to use:

### Currently Using Free Version?

✅ You can use it immediately, no setup needed!

### Want to Switch to Official API?

1. Follow steps above to get API key
2. Create `config.ini` with your key
3. Install `google-cloud-translate`
4. Run the tool - it will automatically use the official API!

### Want to Switch Back to Free?

1. Delete or rename `config.ini`
2. Or remove the `api_key` line from `config.ini`
3. Run the tool - it will use the free version!

---

## 🐛 Troubleshooting

### "No translation service available"

**Problem:** Neither free nor official API is installed

**Solution:**
```bash
pip install googletrans==4.0.0rc1
# OR
pip install google-cloud-translate
```

### "Failed to initialize Cloud API"

**Possible causes:**

1. **Invalid API key**
   - Check your key in `config.ini`
   - Make sure you copied it correctly
   - Try regenerating the key

2. **API not enabled**
   - Go to [Translation API](https://console.cloud.google.com/apis/library/translate.googleapis.com)
   - Click "Enable"

3. **Billing not set up**
   - Go to [Billing](https://console.cloud.google.com/billing)
   - Link a billing account

4. **Wrong credentials path**
   - Check the path in `config.ini`
   - Use full absolute path
   - Make sure the JSON file exists

### "Translation failed after 3 attempts"

**Free version:**
- Rate limiting - wait a few minutes
- Network issues - check internet connection

**Official API:**
- Check quota in [Cloud Console](https://console.cloud.google.com/apis/api/translate.googleapis.com/quotas)
- Verify billing is active
- Check [Service Health](https://status.cloud.google.com/)

### "Quota exceeded"

**Solution:**
- Wait until next month for quota reset
- Or enable billing for higher limits
- Or reduce campaign size

---

## 📊 Monitoring Usage

### Check Your Usage

1. Go to [Translation API Metrics](https://console.cloud.google.com/apis/api/translate.googleapis.com/metrics)
2. View:
   - Number of requests
   - Characters translated
   - Error rates
   - Quota usage

### Check Your Costs

1. Go to [Billing > Reports](https://console.cloud.google.com/billing/reports)
2. Filter by:
   - Service: "Cloud Translation API"
   - Date range
3. View detailed breakdown

---

## ❓ FAQ

### Q: Do I need an API key to use the tool?

**A:** No! The tool works with the free `googletrans` library by default (no API key needed). The API key is optional for better performance.

### Q: Will I be charged for using the official API?

**A:** Not for small usage! Google provides 500,000 free characters per month. A typical campaign uses 50,000-200,000 characters, well within the free tier.

### Q: Which method should I use?

**A:**
- **Free version**: For personal projects, testing, or small campaigns
- **Official API**: For professional use, large campaigns, or if you need reliability

### Q: Can I use both versions?

**A:** Yes! The tool will automatically use the official API if you provide a key, otherwise it falls back to the free version.

### Q: Is my API key safe?

**A:** Yes, if you follow best practices:
- Keep `config.ini` out of version control (already in `.gitignore`)
- Don't share your API key publicly
- Restrict the key to Translation API only

### Q: How do I know which version I'm using?

**A:** When you run the tool, it will print:
- `✓ Using Google Cloud Translation API (Official)` - with API key
- `✓ Using free Google Translate (no API key)` - free version

---

## 🔗 Useful Links

- [Google Cloud Console](https://console.cloud.google.com/)
- [Translation API Documentation](https://cloud.google.com/translate/docs)
- [Translation API Pricing](https://cloud.google.com/translate/pricing)
- [Free Tier Details](https://cloud.google.com/free/docs/gcp-free-tier)
- [API Key Best Practices](https://cloud.google.com/docs/authentication/api-keys)

---

## 📞 Need Help?

1. Check this guide thoroughly
2. Review error messages carefully
3. Test with a small campaign first
4. Check the [main README](README.md) for general troubleshooting

---

**Happy Translating! 🌍🎮**
