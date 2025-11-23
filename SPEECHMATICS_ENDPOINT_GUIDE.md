# How to Get Your Speechmatics Agent WebSocket Endpoint

## From Speechmatics Portal

Based on your agent ID `5a14d0ec-bec2-41a7-8307-34cb13d452f8`, here's how to find your endpoint:

### 1. Agent Information
- **Agent ID**: `5a14d0ec-bec2-41a7-8307-34cb13d452f8`
- **Region**: EU2 (shown in your portal as "Region EU1" - check which region your agent is deployed in)

### 2. WebSocket Endpoint Format

The endpoint format is:
```
wss://{region}.rt.speechmatics.com/v1/agent/{agent_id}/ws
```

For your agent:
```
wss://eu2.rt.speechmatics.com/v1/agent/5a14d0ec-bec2-41a7-8307-34cb13d452f8/ws
```

### 3. Configuration in `.env` file

Add these to your `.env` file:

```env
SPEECHMATICS_API_KEY=your_api_key_here
SPEECHMATICS_AGENT_ID=5a14d0ec-bec2-41a7-8307-34cb13d452f8
SPEECHMATICS_REGION=eu2
```

### 4. Finding Your Region

Check your Speechmatics Portal:
- Look at the left sidebar - it shows "Region EU1" or similar
- Common regions: `eu1`, `eu2`, `us1`, `us2`
- Use the region code that matches your agent's deployment

### 5. Getting Your API Key

1. Go to Speechmatics Portal: https://portal.speechmatics.com/
2. Navigate to API Keys section
3. Create or copy your API key
4. Add it to `.env` file

### 6. Testing the Endpoint

The endpoint is automatically constructed in the code:
- Backend: `/api/speechmatics-credentials/{session_id}` returns the full WebSocket URL
- Frontend: Connects directly to the returned URL

### Important Notes

⚠️ **Browser WebSocket Limitation**: 
- Browser WebSocket API doesn't support custom headers
- The code tries URL-based authentication first: `?authorization=Bearer {token}`
- If that doesn't work, you may need to:
  1. Use a WebSocket library that supports headers (like `reconnecting-websocket`)
  2. Or send authentication in the first message after connection
  3. Or use a minimal proxy that adds headers

### Current Implementation

The system:
1. Fetches credentials from `/api/speechmatics-credentials/{session_id}`
2. Constructs URL: `wss://{region}.rt.speechmatics.com/v1/agent/{agent_id}/ws`
3. Connects directly from frontend to Speechmatics
4. Tries authentication via URL parameter

