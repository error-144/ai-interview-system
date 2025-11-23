# Troubleshooting: 403 Forbidden Error

## Issue
Getting "403 Forbidden" when trying to connect to Speechmatics Flow API LiveKit endpoint.

## Root Cause
The API key (`PLTtZHHtafizQic9phejMX3G64gdb0cA`) does not have permission to access the Flow API LiveKit endpoint.

## Solution Steps

### Step 1: Verify API Key Permissions

1. **Go to Speechmatics Portal:**
   - Visit: https://portal.speechmatics.com/
   - Log in with your account

2. **Check API Key Settings:**
   - Navigate to **API Keys** section
   - Find your API key: `PLTtZHHtafizQic...`
   - Check if it has **Flow API** or **LiveKit** permissions enabled

3. **If Flow API Access is Missing:**
   - Flow API might be a premium feature
   - Contact Speechmatics support to enable Flow API access
   - Or create a new API key with Flow API permissions

### Step 2: Verify Template/Agent ID

1. **Go to Agents Section:**
   - In Speechmatics Portal, navigate to **Agents**
   - Find your agent (ID: `5a14d0ec-bec2-41a7-8307-34cb13d452f8`)
   - Verify the exact Template ID format
   - It should be either:
     - `5a14d0ec-bec2-41a7-8307-34cb13d452f8` (without version)
     - `5a14d0ec-bec2-41a7-8307-34cb13d452f8:latest` (with version)

### Step 3: Test API Key Directly

Run the test script:
```bash
node test-speechmatics.js
```

This will test different configurations and show you exactly what's failing.

### Step 4: Alternative - Use Direct WebSocket (If LiveKit Not Available)

If Flow API LiveKit is not available with your current API key, you can use the direct WebSocket approach:

1. **Update `.env`:**
   ```env
   SPEECHMATICS_API_KEY=your_key
   SPEECHMATICS_AGENT_ID=5a14d0ec-bec2-41a7-8307-34cb13d452f8
   SPEECHMATICS_REGION=eu1
   ```

2. **Use WebSocket endpoint instead:**
   - Endpoint: `wss://flow.api.speechmatics.com/`
   - Requires WebSocket proxy (already implemented in Python version)

## Current Status

✅ **Environment Variables:** Correctly loaded
- API Key: `PLTtZHHtafizQic...` ✓
- Template ID: `5a14d0ec-bec2-41a7-8307-34cb13d452f8:latest` ✓

❌ **API Access:** 403 Forbidden
- API key lacks Flow API LiveKit permissions
- Need to enable Flow API access in Speechmatics Portal

## Next Actions

1. **Contact Speechmatics Support:**
   - Request Flow API LiveKit access for your API key
   - Or ask for a new API key with Flow API permissions

2. **Alternative Solution:**
   - Use the Python backend with WebSocket proxy (already working)
   - Or wait for Flow API access to be enabled

## Testing Voice Agent

Once API access is fixed, test the voice agent:

1. Start the server: `npm start`
2. Start the frontend: `cd frontend && npm run dev`
3. Upload a resume
4. Click "Start Interview"
5. The LiveKit connection should work and you'll hear the agent speak

## Contact Information

- Speechmatics Support: https://www.speechmatics.com/support/
- Portal: https://portal.speechmatics.com/
- Documentation: https://docs.speechmatics.com/flow-api-ref

