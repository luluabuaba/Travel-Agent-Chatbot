### integrating wikipedia


import wikipedia

def get_destination_info(destination: str) -> str:
    try:
        summary = wikipedia.summary(destination, sentences=5, auto_suggest=True)
        return f"📍 **{destination}**:\n{summary}"
    except Exception as e:
        return f"❌ Could not fetch info: {e}"
