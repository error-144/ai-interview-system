# Environment Variables Setup

## Required Credentials

To fix the "Forbidden" error, you need to add these credentials to your `.env` file:

### 1. Speechmatics API Key

Get your API key from: https://portal.speechmatics.com/

Add to `.env`:
```env
SPEECHMATICS_API_KEY=your_speechmatics_api_key_here
```

### 2. Speechmatics Agent/Template ID

This is your agent ID from the Speechmatics Portal. Based on your previous messages, it should be:
```env
SPEECHMATICS_AGENT_ID=5a14d0ec-bec2-41a7-8307-34cb13d452f8
```

Or if you're using a template ID:
```env
SPEECHMATICS_TEMPLATE_ID=your_template_id_here
```

### 3. OpenAI API Key (for resume extraction)

Get your API key from: https://platform.openai.com/api-keys

Add to `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Complete .env File Example

```env
# OpenAI API (for resume extraction and question generation)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
MAX_TOKENS_DEFAULT=250

# Speechmatics Flow API
SPEECHMATICS_API_KEY=your_speechmatics_api_key_here
SPEECHMATICS_AGENT_ID=5a14d0ec-bec2-41a7-8307-34cb13d452f8
# Alternative: SPEECHMATICS_TEMPLATE_ID=your_template_id

# Server
PORT=8000
```

## How to Get Your Speechmatics API Key

1. Go to https://portal.speechmatics.com/
2. Log in to your account
3. Navigate to **API Keys** section
4. Create a new API key or copy an existing one
5. Add it to your `.env` file

## How to Get Your Agent/Template ID

1. Go to https://portal.speechmatics.com/
2. Navigate to **Agents** section
3. Find your agent (e.g., "Mohit" based on your screenshot)
4. Copy the Agent ID (format: `5a14d0ec-bec2-41a7-8307-34cb13d452f8`)
5. Add it to your `.env` file as `SPEECHMATICS_AGENT_ID`

## Troubleshooting

### "Forbidden" Error (403)

This usually means:
- ❌ API key is missing or incorrect
- ❌ API key doesn't have permission to access Flow API
- ❌ Agent ID is incorrect or doesn't exist

**Fix:**
1. Verify your API key is correct
2. Check that your API key has Flow API access enabled
3. Verify your Agent ID matches exactly what's in the portal

### "Unauthorized" Error (401)

This means:
- ❌ API key is invalid or expired

**Fix:**
1. Generate a new API key
2. Update your `.env` file
3. Restart the server

### "Not Found" Error (404)

This means:
- ❌ Agent/Template ID doesn't exist

**Fix:**
1. Check the Agent ID in Speechmatics Portal
2. Make sure you're using the correct ID (not the name)
3. Verify the ID format matches: `uuid:version` or just `uuid`

## After Updating .env

1. **Restart the Node.js server:**
```bash
# Stop the current server (Ctrl+C)
# Then restart:
npm start
```

2. **Clear browser cache** if needed

3. **Check server logs** for confirmation:
```
[API] Using Agent ID/Template ID: 5a14d0ec-bec2-41a7-8307-34cb13d452f8
[API] API Key present: Yes
```

