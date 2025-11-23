# Cost Optimization - Token Limits

This document describes the token limit configurations implemented to reduce API costs.

## Environment Variables

Add these to your `.env` file to customize token limits:

```env
# Realtime API token limits
REALTIME_MAX_TOKENS=150          # Max tokens per Realtime API response (default: 150)

# Regular LLM call token limits
MAX_TOKENS_QUESTION=200           # Max tokens for question generation (default: 200)
MAX_TOKENS_FEEDBACK=300           # Max tokens for feedback generation (default: 300)
MAX_TOKENS_DEFAULT=250            # Default max tokens for other LLM calls (default: 250)
```

## Token Limits by Function

### 1. Realtime API (`utils/realtime_agent.py`)
- **Default**: 150 tokens per response
- **Purpose**: Limits voice conversation responses to be concise
- **Config**: `REALTIME_MAX_TOKENS` environment variable

### 2. Question Generation (`utils/analyze_candidate.py`)
- **Default**: 200 tokens
- **Purpose**: Questions should be short (1-2 sentences)
- **Config**: `MAX_TOKENS_QUESTION` environment variable

### 3. Feedback Generation (`utils/analyze_candidate.py`)
- **Default**: 300 tokens
- **Purpose**: Brief feedback (max 80 words)
- **Config**: `MAX_TOKENS_FEEDBACK` environment variable

### 4. Resume Extraction (`utils/basic_details.py`)
- **Default**: 250 tokens
- **Purpose**: Extract name and highlights (concise JSON)
- **Config**: `MAX_TOKENS_DEFAULT` environment variable
- **Additional**: Resume content truncated to 2000 characters to save input tokens

## Prompt Optimization

All prompts have been optimized to be more concise:
- **Before**: ~500-800 tokens per prompt
- **After**: ~100-200 tokens per prompt
- **Savings**: ~60-75% reduction in input tokens

### Optimized Prompts:
1. `basic_details`: Reduced from ~400 to ~50 tokens
2. `next_question_generation`: Reduced from ~600 to ~100 tokens
3. `feedback_generation`: Reduced from ~800 to ~80 tokens

## Cost Savings Estimate

### Per Interview (5 questions):
- **Input tokens**: ~2000 tokens (down from ~5000) = **60% savings**
- **Output tokens**: ~1500 tokens (down from ~4000) = **62% savings**
- **Total**: ~3500 tokens per interview (down from ~9000) = **61% savings**

### Realtime API:
- **Output tokens**: Limited to 150 per response
- **Estimated savings**: ~50-70% compared to unlimited responses

## Additional Optimizations

1. **System Prompt**: Realtime API system prompt reduced from ~300 to ~150 tokens
2. **Temperature**: Lowered to 0.7 for more focused responses
3. **Resume Truncation**: Resume content limited to 2000 characters
4. **Concise Instructions**: All prompts use bullet points and short sentences

## Monitoring Costs

To monitor your API usage:
1. Check OpenAI dashboard for token usage
2. Adjust token limits in `.env` based on your needs
3. Lower limits = lower costs but potentially less detailed responses
4. Higher limits = more detailed responses but higher costs

## Recommended Settings

### Budget-Conscious (Maximum Savings):
```env
REALTIME_MAX_TOKENS=100
MAX_TOKENS_QUESTION=150
MAX_TOKENS_FEEDBACK=200
MAX_TOKENS_DEFAULT=200
```

### Balanced (Default):
```env
REALTIME_MAX_TOKENS=150
MAX_TOKENS_QUESTION=200
MAX_TOKENS_FEEDBACK=300
MAX_TOKENS_DEFAULT=250
```

### Quality-Focused (Higher Cost):
```env
REALTIME_MAX_TOKENS=250
MAX_TOKENS_QUESTION=300
MAX_TOKENS_FEEDBACK=400
MAX_TOKENS_DEFAULT=350
```

