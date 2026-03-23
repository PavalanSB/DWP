# Google OAuth Configuration Guide

## Overview
This application uses Google OAuth for user authentication and account deletion confirmation. Proper configuration of redirect URIs in Google Cloud Console is critical for the app to work correctly.

## Required Redirect URIs for Google Cloud Console

Add **ALL** of the following URLs to your Google OAuth 2.0 Client's "Authorized redirect URIs" section:

### For Development (localhost:5000)
```
http://localhost:5000/auth/google/callback
http://localhost:5000/settings/delete-account/confirm/google
```

### For Production
Replace `localhost:5000` with your actual domain (with https):
```
https://yourdomain.com/auth/google/callback
https://yourdomain.com/settings/delete-account/confirm/google
```

## How to Add Redirect URIs in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project → APIs & Services → Credentials
3. Click on your OAuth 2.0 Client ID (Web application)
4. Under "Authorized redirect URIs" section, click **+ Add URI**
5. Paste **each** of the URLs above exactly as shown
6. Click **Save**

⚠️ **Important:** 
- The protocol (`http://` vs `https://`), domain, port, and path must match **exactly**
- No trailing slashes
- URIs are case-sensitive

## What Each Redirect URI Does

### `/auth/google/callback`
- Used when user clicks "Sign in with Google" on the login page
- Handles normal OAuth authentication flow
- Creates new user account if first-time login

### `/settings/delete-account/confirm/google`
- Used when user tries to delete their account with Google OAuth
- Re-authenticates user with Google to confirm account deletion
- Deletes user account and all associated data only after confirmation

## Troubleshooting

### Error: "redirect_uri_mismatch"
**Cause:** The redirect URI used by the application doesn't match what's registered in Google Console.

**Solution:** 
- Check that the URI is exactly as listed above
- Verify there are no extra spaces or trailing slashes
- Make sure you're using the correct domain/port

### Error: "This app's request is invalid"
**Cause:** Usually accompanies redirect_uri_mismatch. Google is rejecting the OAuth request.

**Solution:**
- Verify all required redirect URIs are added to Google Console
- Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct
- Ensure these are set in your `.env` file:
  ```
  GOOGLE_CLIENT_ID=your_client_id_here
  GOOGLE_CLIENT_SECRET=your_client_secret_here
  ```

## Testing the Setup

1. **Test normal login:**
   - Go to http://localhost:5000/
   - Click "Login" → "Sign in with Google"
   - If redirect_uri_mismatch appears, check URIs in Google Console

2. **Test account deletion with OAuth:**
   - Log in with Google
   - Go to Settings → Delete Account
   - Enter your password (if set) or proceed with re-auth
   - Should redirect to Google for confirmation
   - After confirming, account should be deleted and you logged out
   - Trying to log back in with same email should create a new account

## Environment Variables

Ensure your `.env` file contains:
```
GOOGLE_CLIENT_ID=your_client_id_from_google_console
GOOGLE_CLIENT_SECRET=your_client_secret_from_google_console
```

Never commit these secrets to version control.

## Key Changes Made to Fix Issues

1. **Consistent Redirect URI Generation**: Both login and delete flows now use the same `_external=True` parameter for URL generation
2. **Improved Error Handling**: Account deletion now properly clears all sessions and cookies
3. **Better Error Messages**: Users now see specific guidance when redirect_uri_mismatch occurs
4. **Session Cleanup**: Complete session clearing after account deletion prevents auto-login to deleted accounts

## Support

If issues persist:
1. Check Google Cloud Console for correct credentials
2. Verify all redirect URIs are exactly as specified
3. Clear browser cookies and cached data
4. Try in an incognito/private window to test with fresh session
5. Check application logs for detailed error messages
