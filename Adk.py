#!/usr/bin/env python3
"""
ADK Agent with LangFuse Logging
Gemini 2.5 Flash with Web Search
Extracted from combined system
"""

import google.generativeai as genai
import os
import requests
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "your-public-key")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "your-secret-key")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

langfuse = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)

genai.configure(api_key=GEMINI_API_KEY)


web_search_tool = {
    "function_declarations": [{
        "name": "web_search",
        "description": "Search the web for current information, news, facts, or real-time data",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information"
                }
            },
            "required": ["query"]
        }
    }]
}

@observe()
def execute_web_search(query):
    print(f"🔍 Executing search: '{query}'")
    
    # Log to LangFuse
    langfuse_context.update_current_trace(
        name="web_search",
        metadata={"query": query}
    )
    
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Extract relevant information
        result = []
        
        if data.get("AbstractText"):
            result.append(f"Summary: {data['AbstractText']}")
        
        if data.get("Answer"):
            result.append(f"Answer: {data['Answer']}")
            
        if data.get("RelatedTopics"):
            topics = []
            for topic in data["RelatedTopics"][:3]:
                if isinstance(topic, dict) and "Text" in topic:
                    topics.append(topic["Text"])
            if topics:
                result.append(f"Related: {', '.join(topics)}")
        
        if result:
            search_result = "\n".join(result)
        else:
            # Fallback: use Gemini to answer
            print("⚠️ No results from search API, using Gemini knowledge")
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content(
                f"Please provide current information about: {query}. "
                f"If you don't have current information, say so."
            )
            search_result = response.text
        
        # Log result to LangFuse
        langfuse_context.update_current_observation(
            output=search_result
        )
        
        return search_result
            
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        print(f"⚠️ {error_msg}")
        
        langfuse_context.update_current_observation(
            level="ERROR",
            status_message=error_msg
        )
        
        return error_msg

@observe()
def run_adk_agent(user_query):
    """
    ADK Agent Loop with LangFuse logging:
    1. Model decides if it needs web search
    2. If yes → execute search tool
    3. Model processes results
    4. Return final answer
    """
    
    # Log to LangFuse
    langfuse_context.update_current_trace(
        name="adk_agent",
        input=user_query,
        metadata={"model": "gemini-2.5-flash"}
    )
    
    # Create agent model with tool
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        tools=[web_search_tool]
    )
    
    print(f"\n{'='*70}")
    print(f"ADK AGENT - USER: {user_query}")
    print(f"{'='*70}\n")
    
    # Start chat
    chat = model.start_chat()
    response = chat.send_message(user_query)
    
    # Agent loop
    max_iterations = 5
    iteration = 0
    tool_calls = []
    
    while iteration < max_iterations:
        has_function_call = False
        
        try:
            if (response.candidates and 
                len(response.candidates) > 0 and
                response.candidates[0].content.parts and
                len(response.candidates[0].content.parts) > 0):
                
                first_part = response.candidates[0].content.parts[0]
                
                if hasattr(first_part, 'function_call') and first_part.function_call:
                    function_call = first_part.function_call
                    has_function_call = True
                    
                    function_name = function_call.name
                    
                    if function_call.args:
                        function_args = dict(function_call.args)
                    else:
                        function_args = {}
                    
                    print(f"🤖 Agent decided to use: {function_name}")
                    print(f"   Arguments: {function_args}\n")
                    
                    # Log tool call
                    tool_calls.append({
                        "function": function_name,
                        "arguments": function_args
                    })
                    
                    # Execute the tool
                    if function_name == "web_search":
                        tool_result = execute_web_search(function_args.get("query", ""))
                        print(f"✅ Search completed\n")
                    else:
                        tool_result = "Unknown tool"
                    
                    # Send result back to model
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": tool_result}
                                )
                            )]
                        )
                    )
                    
                    iteration += 1
                    
        except Exception as e:
            print(f"⚠️ Error in function call handling: {e}")
            has_function_call = False
        
        if not has_function_call:
            break
    
    # Get final answer
    try:
        final_answer = response.text
    except:
        final_answer = "Agent completed processing"
        if response.candidates and len(response.candidates) > 0:
            parts = response.candidates[0].content.parts
            for part in parts:
                if hasattr(part, 'text') and part.text:
                    final_answer = part.text
                    break
    
    print(f"{'='*70}")
    print(f"ADK AGENT FINAL ANSWER:")
    print(f"{'='*70}")
    print(final_answer)
    print(f"{'='*70}\n")
    
    # Log final result to LangFuse
    langfuse_context.update_current_trace(
        output=final_answer,
        metadata={
            "tool_calls": tool_calls,
            "iterations": iteration
        }
    )
    
    return final_answer

# ============================================================================
# MAIN EXECUTION
# ============================================================================

@observe()
def main():
    """Main function - runs ADK agent with example queries"""
    
    print("\n" + "="*70)
    print("🚀 ADK AGENT WITH WEB SEARCH & LANGFUSE LOGGING")
    print("="*70)
    
    # Example queries
    adk_queries = [
        "What is 10 + 25?",
        "Name 3 popular car brands"
    ]
    
    for query in adk_queries:
        try:
            run_adk_agent(query)
        except Exception as e:
            print(f"❌ Error: {e}")
        print("\n")
    
    print("="*70)
    print("✅ ALL QUERIES COMPLETED")
    print("="*70)
    print(f"\n📊 View logs in LangFuse: {LANGFUSE_HOST}")
    
    # Flush LangFuse to ensure all logs are sent
    langfuse.flush()

if __name__ == "__main__":
    main()
