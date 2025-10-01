# Google OAuth Setup Guide for InfraZen

This guide will help you set up Google OAuth authentication for the InfraZen FinOps platform.

## Prerequisites

- Google account
- Access to Google Cloud Console
- InfraZen application running locally

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `InfraZen-FinOps` (or any name you prefer)
4. Click "Create"

## Step 2: Enable Google+ API

1. In your new project, go to "APIs & Services" → "Library"
2. Search for "Google+ API" 
3. Click on it and press "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields:
     - App name: `InfraZen FinOps Platform`
     - User support email: your email
     - Developer contact: your email
   - Add scopes: `email`, `profile`, `openid`
   - Add test users: your email address
4. Application type: "Web application"
5. Name: `InfraZen Web Client`
6. Authorized redirect URIs: 
   - `http://localhost:5001/auth/google/callback`
   - `http://127.0.0.1:5001/auth/google/callback`

## Step 4: Get Client ID

1. After creating credentials, copy the "Client ID" (it looks like: `123456789-abcdefg.apps.googleusercontent.com`)
2. Keep this handy for the next step

## Step 5: Configure InfraZen

1. Copy the example config file:
   ```bash
   cp config.env.example config.env
   ```

2. Edit `config.env` and add your Google Client ID:
   ```bash
   GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
   ```

## Step 6: Test the Setup

1. Restart your InfraZen server:
   ```bash
   # Kill existing server (Ctrl+C)
   python src/main.py
   ```

2. Go to `http://localhost:5001/login`
3. You should see the Google Sign-In button
4. Click it and test with your Google account

## Troubleshooting

### "Error 400: redirect_uri_mismatch"
- Make sure your redirect URI in Google Console exactly matches: `http://localhost:5001/auth/google/callback`
- Check that the port (5001) matches your server

### "This app isn't verified"
- This is normal for development. Click "Advanced" → "Go to InfraZen FinOps Platform (unsafe)"
- For production, you'll need to verify your app with Google

### "Access blocked"
- Make sure your email is added as a test user in OAuth consent screen
- Check that you're using the correct Google account

### Google Sign-In button doesn't appear
- Check browser console for JavaScript errors
- Verify `GOOGLE_CLIENT_ID` is set correctly in `config.env`
- Make sure the server restarted after adding the config

## Production Deployment

For production deployment, you'll need to:

1. Add your production domain to authorized origins and redirect URIs
2. Complete OAuth consent screen verification
3. Update `config.env` with production settings
4. Consider using environment variables instead of config files

## Security Notes

- Never commit `config.env` to version control
- Keep your Client ID and Client Secret secure
- Use HTTPS in production
- Regularly rotate credentials

## Need Help?

If you encounter issues:
1. Check the server logs for error messages
2. Verify all steps were completed correctly
3. Test with a fresh Google account
4. Check Google Cloud Console for any error messages

The demo login will always work as a fallback if Google OAuth isn't configured.






