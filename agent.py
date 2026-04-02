from tools.wiki_tool import get_destination_info
from tools.calendar_tool import schedule_event
from tools.flight_tool import get_flight_info
from openai import OpenAI
import re
import os
import streamlit as st
import json
from dotenv import load_dotenv

MODEL = 'gpt-4o-mini'
ai_client = OpenAI()

# Safety check
def is_safe(client, user_input):
    try:
        moderation = client.moderations.create(
            input=user_input,
            model='omni-moderation-latest'
        )
        result = moderation.results[0]
        return not result.flagged
    except Exception as e:
        print(f"⚠️ Moderation error: {e}")
        return False

# Determines if a user input is a question
def is_question(text):
    return "?" in text or re.match(r"(?i)\b(who|what|when|where|why|how|which)\b", text.strip())

# Prompt setting
SYSTEM_PROMPT = """
You are a friendly travel agent bot who helps users plan trips. Your job is to assist users in exploring destinations, booking flights, and building itineraries that are informative, delightful, and tailored to their needs.

---

### How You Work (Agent Loop)

You follow a loop of reasoning and action:

1. **Interpret the user’s goal** — Understand what the user wants based on their message.
2. **Reason about what to do next** — Decide on the next action (e.g., get info, find flights).
3. **Select a tool (if needed)** — Choose one of the available tools listed below.
4. **Execute the tool** — Call the tool with appropriate inputs and get results.
5. **Observe the result** — Decide whether the tool gave the needed info.
6. **Repeat steps 2–5** — Keep going until the task is complete or you need clarification.

You must always check the outcome of each step before continuing. Ask follow-up questions when information is missing or unclear.

---

### Available Tools

**Wikipedia Tool** (`get_destination_info`)  
- **Purpose**: Retrieve summaries and helpful details about a destination, city, or attraction.  
- **Use When**:  
  - The user asks about a place ("Tell me about Paris", "What's there to do in Seoul?")
  - You’re building or enriching an itinerary.
  - Background on a location would improve your answer.

**Flight Tool** (`get_flight_info`)  
- **Purpose**: Search for flights between an origin and destination on a specific date (and optional return date).  
- **Use When**:  
  - The user mentions travel between cities ("from New York to Rome").
  - A travel date is provided or implied.
  - You have parsed origin, destination, and travel date.
  - Only if `SERPAPI_KEY` is available.

**Calendar Tool** (`schedule_event`)  
- **Purpose**: Add activities (like “Explore Rome”) to a calendar on specific dates and times.  
- **Use When**:  
  - Destination and travel date are known.
  - You want to suggest or confirm an activity.
  - To help structure an itinerary.
  - Input must include a valid date (e.g., "July 2025" or "2025-07-01").

**Safety Filter** (`is_safe`)  
- **Purpose**: Check user input for unsafe or inappropriate content.  
- **Use When**:  
  - Before responding to **any** user message.
  - If flagged, do not proceed; inform the user the message was flagged.

**Question Detector** (`is_question`)  
- **Purpose**: Check whether user input is a question.  
- **Use When**:  
  - To determine if Wikipedia info would help answer.
  - To better understand if the user is asking vs. planning.

---

### Your Planning Strategy

You should reason about the user input by first checking if it is **safe**, then parsing for:

- Origin city  
- Destination  
- Outbound date  
- Return date (optional)  
- Budget (optional)  
- Interests (optional)

Use the tools in sequence depending on what is known and what’s missing. Always aim to deliver a smooth, engaging, and helpful travel planning experience.
"""





# Conversation history for in-memory use
conversation_history = [{'role': 'system', 'content': SYSTEM_PROMPT}]

### STREAMLIT APP ###
if "messages" not in st.session_state:
    st.session_state.messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
if "itinerary" not in st.session_state:
    st.session_state.itinerary = {}

st.title("Travel Agent 🛫")
st.caption("I'm here to help you plan your next trip!")

# chat history
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# User input
user_input = st.chat_input("Your trip awaits! What do you have in mind?")

if user_input:
    if not is_safe(ai_client, user_input):
        st.chat_message("assistant").markdown("⚠️ Sorry, that message was flagged as unsafe.")
    else:
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Get Wikipedia info if it's a question
        if is_question(user_input):
            wiki_info = get_destination_info(user_input)
            query_with_context = f"{user_input}\n\nHere is some relevant information from Wikipedia:\n{wiki_info}"
        else:
            query_with_context = user_input

        # Create model messages
        messages_for_model = st.session_state.messages + [{"role": "user", "content": query_with_context}]

        # Call OpenAI
        try:
            response = ai_client.chat.completions.create(
                model=MODEL,
                messages=messages_for_model,
                temperature=0.7
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"⚠️ Error getting response: {e}"

        # Show assistant reply
        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Parse user input for scheduling
        planning_prompt = f"""
        User input: {user_input}
        Parse the input to extract:
        - Origin city
        - Destination
        - Outbound travel date (e.g., 'July 2025' or '2025-07-01')
        - Return date (if provided, e.g., '2025-07-10')
        - Budget (if provided)
        - Interests (if provided)

        Create a list of sub-tasks to complete the itinerary. Each item should be a short description in plain text, like:

        [
        "Fetch destination info",
        "Find flights from New York to Paris on 2025-07-01",
        "Schedule activities in Paris for 2025-07-01"
        ]

        Respond with **only valid JSON**. Do not add explanation or formatting.

        """
        try:
            planning_response = ai_client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": planning_prompt}],
                temperature=0.7
            )
            content = planning_response.choices[0].message.content.strip()
            
            if not content:
                raise ValueError("Empty response from model")

            sub_tasks = json.loads(planning_response.choices[0].message.content)
            st.session_state.task_state = sub_tasks
            
            # Output the plan to the user
            st.chat_message("assistant").markdown("📋 Here's the plan I'm following:")
            for i, task in enumerate(sub_tasks, 1):
                st.chat_message("assistant").markdown(f"{i}. {task}")


        except Exception as e:
            sub_tasks = ["Error parsing input"]
            st.session_state.task_state = sub_tasks
            st.chat_message("assistant").markdown(f"⚠️ Error planning tasks: {e}")

        # Execute sub-tasks
        itinerary = st.session_state.itinerary
        for task in st.session_state.task_state:
            if "fetch destination info" in task.lower():
                destination_match = re.search(r"(?:to|in)\s+([A-Za-z\s]+?)(?:\s+(?:in|on|from|return|$))", user_input, re.IGNORECASE)
                if destination_match:
                    destination = destination_match.group(1).strip()
                    wiki_info = get_destination_info(destination)
                    itinerary["destination_info"] = wiki_info
                    st.chat_message("assistant").markdown(f"📍 Destination Info:\n{wiki_info}")
                else:
                    st.chat_message("assistant").markdown("⚠️ Could not identify destination. Please specify (e.g., 'to Paris').")
            elif "find flights" in task.lower():
                origin_match = re.search(r"(?:from)\s+([A-Za-z\s]+?)(?:\s+to|\s+in)", user_input, re.IGNORECASE)
                destination_match = re.search(r"(?:to|in)\s+([A-Za-z\s]+?)(?:\s+(?:in|on|from|return|$))", user_input, re.IGNORECASE)
                date_match = re.search(r"(?:in|on)\s+((?:[A-Za-z]+ \d{4})|(?:\d{4}-\d{2}-\d{2}))", user_input, re.IGNORECASE)
                return_date_match = re.search(r"(?:return\s*(?:on|in)?)\s*(\d{4}-\d{2}-\d{2})", user_input, re.IGNORECASE)
                
                if origin_match and destination_match and date_match:
                    origin = origin_match.group(1).strip()
                    destination = destination_match.group(1).strip()
                    date = date_match.group(1).strip()
                    return_date = return_date_match.group(1) if return_date_match else None
                    
                    flight_info = get_flight_info(
                        origin=origin,
                        destination=destination,
                        date=date,
                        return_date=return_date
                    )
                    
                    if "error" in flight_info:
                        st.chat_message("assistant").markdown(f"⚠️ Flight Error: {flight_info['error']}")
                    else:
                        itinerary["flights"] = flight_info
                        st.chat_message("assistant").markdown(f"✈️ Flight Info:\n{json.dumps(flight_info, indent=2)}")
                else:
                    missing = []
                    if not origin_match: missing.append("origin city")
                    if not destination_match: missing.append("destination")
                    if not date_match: missing.append("travel date")
                    st.chat_message("assistant").markdown(f"⚠️ Please specify {', '.join(missing)} (e.g., 'from New York to Paris in July 2025').")
            elif "schedule activities" in task.lower():
                destination_match = re.search(r"(?:to|in)\s+([A-Za-z\s]+?)(?:\s+(?:in|on|from|return|$))", user_input, re.IGNORECASE)
                date_match = re.search(r"(?:in|on)\s+((?:[A-Za-z]+ \d{4})|(?:\d{4}-\d{2}-\d{2}))", user_input, re.IGNORECASE)
                if destination_match and date_match:
                    destination = destination_match.group(1).strip()
                    date = date_match.group(1).strip()
                    # Convert date to YYYY-MM-DD for calendar
                    try:
                        if '-' in date:
                            event_date = date
                        else:
                            event_date = f"{date.replace(' ', '-')}-01"
                        activity = f"Explore {destination}"
                        event_link = schedule_event(
                            title=activity,
                            date=event_date,
                            start_time="09:00",
                            end_time="12:00",
                            location=destination
                        )
                        itinerary["activities"] = itinerary.get("activities", []) + [event_link]
                        st.chat_message("assistant").markdown(f"🗓️ {event_link}")
                    except Exception as e:
                        st.chat_message("assistant").markdown(f"⚠️ Error scheduling activity: {e}")
                else:
                    st.chat_message("assistant").markdown("⚠️ Please specify destination and date for activities.")

        # Synthesize and present itinerary
        if itinerary:
            itinerary_summary = f"""
            ### Your Travel Itinerary
            **Destination Info**: {itinerary.get('destination_info', 'Not available')}
            **Flights**: {json.dumps(itinerary.get('flights', {}), indent=2)}
            **Activities**: {', '.join(itinerary.get('activities', ['None scheduled']))}
            """
            st.chat_message("assistant").markdown(itinerary_summary)
            st.session_state.messages.append({"role": "assistant", "content": itinerary_summary})

            # Ask for feedback
            st.chat_message("assistant").markdown("Would you like to adjust anything in this itinerary? (e.g., change dates, add activities)")
            st.session_state.feedback_mode = True
else:
    if st.session_state.itinerary:
        st.chat_message("assistant").markdown("Please provide feedback or a new trip request to continue!")