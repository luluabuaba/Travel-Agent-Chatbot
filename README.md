# Project-04

# Travel Agent Bot

## Overview

**Travel Agent** is a conversational assistant that helps users plan trips by answering questions about destinations and suggesting activities using live data from Wikipedia. The assistant is designed to provide natural, engaging responses that help users explore cities, cultural landmarks, and travel options around the world.

The chatbot is built on OpenAI's GPT-4o-mini model and integrated with moderation tools to ensure a safe user experience. It uses a Wikipedia tool for real-time information retrieval instead of a static document database, offering users up-to-date context without relying on preloaded documents or embeddings.

## Design Details

### Live Wikipedia Retrieval
- Uses a get_destination_info() tool that fetches Wikipedia content.
- Allows the assistant to answer questions about real cities, attractions, or travel-related terms using current public data.

### Safety and Moderation
- Rejects out-of-scope inputs.
- Designed to prevent **prompt injection**.
- Includes moderation logic and strict response filtering for safety.





## Usage Instructions

1. **Start a Conversation** 
Launch the chatbot using Streamlit:
    streamlit run agent.py

2. **Ask Travel Questions**
Type something like:
    "I'm planning a trip to Japan—what should I see in Kyoto?"

3. **Get Informed Suggestions**
The bot fetches Wikipedia summaries and responds:
    “Kyoto is known for its classical Buddhist temples...”

4. **Safe and Focused Interaction**
If unsafe or off-topic input is detected, it politely declines:
    “⚠️ Sorry, I can’t respond to that request.”

5. **Session Memory**
Your messages are remembered during the chat session only. The assistant builds its responses based on the full conversation context.


Project Outline
Task & User Focus
The bot helps users gather information and inspiration for travel by answering questions and suggesting activities. It is not a booking agent or itinerary builder (yet), but supports early planning and discovery.

Scope of Chatbot Responses

Destination facts, travel tips, site recommendations

Flight information, scheduling assistance based on calendar information, planning help

Chatbot does NOT share general knowledge, jokes, unrelated topics

The agent stays task-focused and conversational while using current data.
