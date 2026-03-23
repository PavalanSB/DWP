# Quick Configuration Checklist

## Google Cloud Console Setup

Based on your current setup, here's what needs to be verified/added:

### Current Configuration (From Screenshot)
✅ Project: DWPproj  
✅ Client Type: Web application  
✅ Already has authorized redirect URIs:
- `http://localhost:5000/settings/delete-account/confirm/google`
- `http://localhost:5000/auth/google/callback`

### ✅ Good News!
Your authorized redirect URIs are **already correctly configured** for both:
1. Normal Google login (`/auth/google/callback`)
2. Account deletion re-auth (`/settings/delete-account/confirm/google`)

### What To Do

Since your URIs are correct, the `redirect_uri_mismatch` error is likely due to one of these reasons:

#### Option 1: Environment Variables Not Set
Check your `.env` file has:
```
GOOGLE_CLIENT_ID=your_actual_client_id
GOOGLE_CLIENT_SECRET=your_actual_client_secret
```

**To find these:**
- In Google Cloud Console, go to Credentials
- Click your OAuth 2.0 Client ID
- Copy the "Client ID" and "Client secret" values

#### Option 2: .env File Not Being Read
Ensure your `.env` file is in the project root:
```
c:\Users\ADMIN\Downloads\DWP\.env
```

And contains:
```
GOOGLE_CLIENT_ID=10069398190...
GOOGLE_CLIENT_SECRET=GOCSPX-...
```

#### Option 3: Clear Browser Cache
The redirect_uri_mismatch might be cached. Try:
1. Clear all cookies for localhost:5000
2. Open DevTools → Application → Clear all site data
3. Close browser completely
4. Reopen and try again

#### Option 4: Check Flask App is Using Fresh Config
Try restarting your Flask app:
```bash
# Stop the current running app
# Edit if needed
# Restart with: python app.py
# or: flask run
```

### Verification Steps

1. **Check Environment Variables Are Loaded:**
   - Add this to app.py temporarily after `load_dotenv()`:
   ```python
   print(f"CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID', 'NOT SET')}")
   print(f"CLIENT_SECRET: {os.environ.get('GOOGLE_CLIENT_SECRET', 'NOT SET')}")
   ```
   - Run the app and check console output

2. **Verify OAuth Registration:**
   - Look for log output like: "Google OAuth registered" or check app.oauth.google exists

3. **Test the Login Flow:**
   - Visit http://localhost:5000/
   - Click "Sign in with Google"
   - If it works, you should be redirected to Google login
   - After login, should return to `/auth/google/callback` without errors

### If redirect_uri_mismatch Still Occurs

The error message now includes helpful info. Look for:
- "Redirect URI mismatch. Please ensure 'http://localhost:5000/auth/google/callback' is registered..."

This means the code successfully caught the OAuth error. The issue is definitely with Google Console setup.

**Double-check:**
1. Client ID in `.env` matches the one in Google Console
2. Client Secret in `.env` matches exactly (typos matter!)
3. Redirect URIs match exactly (spacing, http vs https, port number)
4. Client ID belongs to your project (DWPproj)

### Production Deployment

When you deploy to production:

1. **Update Google Cloud Console with production domain:**
   - Add: `https://yourdomain.com/auth/google/callback`
   - Add: `https://yourdomain.com/settings/delete-account/confirm/google`
   - Remove or keep localhost URIs (for testing)

2. **Update environment variables:**
   - May need separate CLIENT_ID/SECRET for production (create new OAuth client in Google Console)
   - Set in your production environment (not in .env, use server/platform env vars)

3. **Update Flask config if needed:**
   - Remove `OAUTH_BASE_URL` config if used (not needed with our fix)
   - Ensure Flask app detects correct domain for `url_for(..., _external=True)`

### Still Having Issues?

Check these files:
- [OAUTH_SETUP.md](OAUTH_SETUP.md) - Detailed setup guide
- [BUGFIXES.md](BUGFIXES.md) - Complete explanation of all fixes
- [views/auth.py](views/auth.py) - Login flow code
- [views/settings.py](views/settings.py) - Account deletion and re-auth code

All fixes have been applied and tested for syntax correctness. The issue should be resolved once you verify your `.env` file has the correct credentials.
