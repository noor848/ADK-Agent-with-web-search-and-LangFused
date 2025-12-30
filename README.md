# ADK Agent with LangFuse
**Extracted from Combined System**

Simple Gemini AI agent with web search and complete observability.

## What This Does

- 🤖 **Gemini AI**: Uses Google's Gemini 2.5 Flash model
- 🔍 **Web Search**: Automatically searches DuckDuckGo when needed
- 📊 **LangFuse Logging**: Tracks every query, search, and response

## Quick Start

### 1. Install Dependencies

```bash
pip install google-generativeai langfuse requests
```

### 2. Set Environment Variables

```bash
# Required: Gemini API Key
export GEMINI_API_KEY="your-gemini-api-key"

# Required: LangFuse Keys
export LANGFUSE_PUBLIC_KEY="your-public-key"
export LANGFUSE_SECRET_KEY="your-secret-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

### 3. Get API Keys

**Gemini API Key:**
- Visit: https://makersuite.google.com/app/apikey
- Create new API key
- Copy and set as `GEMINI_API_KEY`

**LangFuse Keys:**
- Sign up: https://langfuse.com
- Create a project
- Copy public and secret keys

### 4. Run the Agent

```bash
python adk_extracted.py
```

## How It Works

```
User Query
    ↓
Gemini Decides: "Need web search?"
    ↓
Yes → DuckDuckGo Search → Process Results
No  → Direct Answer
    ↓
Final Answer
    ↓
Everything Logged to LangFuse
```
