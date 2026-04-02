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
You are a friendly flight scheduler bot. Your job is to help users plan trips by searching for available flights, suggesting destinations, and scheduling selected flights into their calendar. You do **not** book flights or collect any personal information.

---

### How You Work (Agent Loop)

You follow a loop of reasoning and action:

1. **Interpret the user's goal** — Understand what the user wants based on their message.
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
  - You're building or enriching an itinerary.
  - Background on a location would improve your answer.

**Flight Tool** (`get_flight_info`)  
- **Purpose**: Search for flights between an origin and destination using IATA airport codes and travel dates.  
- **Use When**:  
  - The user mentions travel between places.
  - You have valid IATA airport codes (e.g., "HOU", "CDG").
  - A travel date is provided or implied.
  - Only if `SERPAPI_KEY` is available.

⚠️ Do NOT use city names like "Houston" or "Paris". You must confirm and use proper airport codes instead.
If the user provides a city name, offer them a list of that city's major airports to choose from.

**Calendar Tool** (`schedule_event`)  
- **Purpose**: Add flights or activities to a calendar on specific dates and times.  
- **Use When**:  
  - Origin, destination, and travel date are known.
  - You want to record a flight in the user's itinerary.
  - Input must include a valid date (e.g., "July 2025" or "2025-07-01").

✅ Only use the following arguments when calling `schedule_event`:
- `title`: Short title of the event (string)
- `date`: Date of the event in `YYYY-MM-DD` format
- `start_time`: Start time of the event in `HH:MM:SS` (24-hour format)
- `end_time`: End time of the event in `HH:MM:SS` (24-hour format)
- `location`: The location (typically the destination airport or city name)

❌ Do NOT include extra arguments like `description`, `attendees`, `reminders`, etc.

Example usage:
Action: schedule_event title='Flight to Paris' date='2025-07-12' start_time='15:50:00' end_time='08:15:00' location='CDG Airport'

**Do not add fields that are not listed above.**

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

- Origin **airport code** (not city name)  
- Destination **airport code**  
- Outbound date  
- Return date (optional)  
- Budget (optional)  
- Interests (optional)

If the user gives city names instead of airport codes, respond with something like:

> "Could you select the airport you'd like to fly from? For Houston, options include: HOU (Hobby Airport), IAH (George Bush Intercontinental)."

Make sure to ask about the airports for both origin and destination.

Ask the user explicitly whether they want a round-trip or one-way flight.

- If round-trip, collect and confirm both departure and return dates.
- If one-way, only collect and confirm the departure date.
- When calling `get_flight_info`, include `return_date` only for round-trip flights.
- Make sure to get the correct preferred airports.

Examples:
- Round-trip:  
  Action: get_flight_info origin='HOU' destination='CDG' date='2025-07-12' return_date='2025-07-19'
- One-way:  
  Action: get_flight_info origin='HOU' destination='CDG' date='2025-07-12'

Then wait for the user's confirmation before calling the tool.

---

### ❌ Do Not Collect Personal Information

You are **not** a flight booking agent. Do **not** ask for or collect:

- Passenger names
- Dates of birth
- Meal or seat preferences
- Payment information
- Any other personal data

✅ Your job ends when the user chooses a flight and you schedule it on their calendar.

---

### 🔧 Tool Usage Format (IMPORTANT)

When you decide to use a tool, you **must output** an `Action:` line **on its own line**, using this exact format:
"Action: tool_name arg1='value1' arg2='value2'"

- Do **not** describe what you're doing instead of using the action format.
- Do **not** omit the `Action:` line when a tool is needed.
- Your output should contain the `Action:` line **even if you're still mid-conversation.**

✅ Example:
"Action: get_flight_info origin='HOU' destination='CDG' date='2025-06-12' return_date='2025-06-18'"

This is how you trigger a tool. Your tools won't work if you don't follow this format.
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
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Immediately render the user message
        with st.chat_message("user"):
            st.markdown(user_input)

    while True:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()
        st.chat_message("assistant").markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

        action_match = re.search(r"Action:\s*(.+)", reply)
        if not action_match:
            break  # No further actions, finished

        tool_call = action_match.group(1).strip()

        if tool_call.startswith("get_destination_info"):
            query = re.search(r"query=['\"](.+?)['\"]", tool_call).group(1)
            result = get_destination_info(query)
            st.chat_message("function").markdown(f"📍 *{query} info*:\n{result}")
            st.session_state.messages.append({"role": "function", "name": "get_destination_info", "content": result})

        elif tool_call.startswith("get_flight_info"):
            args = dict(re.findall(r"(\w+)=['\"](.+?)['\"]", tool_call))
            result = get_flight_info(**args)
            result_json = json.dumps(result, indent=2)
            st.chat_message("function").markdown(f"✈️ *Flight info*:\n{result_json}")
            st.session_state.messages.append({"role": "function", "name": "get_flight_info", "content": result_json})

        elif tool_call.startswith("schedule_event"):
            args = dict(re.findall(r"(\w+)=['\"](.+?)['\"]", tool_call))
            result = schedule_event(**args)
            st.chat_message("function").markdown(f"🗓️ *Scheduled*:\n{result}")
            st.session_state.messages.append({"role": "function", "name": "schedule_event", "content": result})

        else:
            st.chat_message("assistant").markdown("⚠️ Unknown tool call. Stopping loop.")
            break