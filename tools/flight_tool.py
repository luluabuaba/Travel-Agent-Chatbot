from serpapi import GoogleSearch
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

# print("SERPAPI_KEY:", SERPAPI_KEY)
def get_flight_info(origin, destination, date, return_date=None):
    try:
        # Validate inputs
        if not SERPAPI_KEY:
            return {"error": "SERPAPI_API_KEY is not set."}
        
        # Configure SerpAPI parameters
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date,
            "return_date": return_date,
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }
        if return_date:
            params["return_date"] = return_date

        # Perform the flight search
        search = GoogleSearch(params)
        results = search.get_dict()

        # print(f"SEARCH: {search}")
        # print(f"RESULTS: {results}")

        # Extract flight information
        if "best_flights" not in results or not results["best_flights"]:
            return {"error": f"No flights found from {origin} to {destination} on {date}"}


        # Simplify flight data for itinerary
        flight_info = []
        for flight_option in results["best_flights"][:3]:  # Limit to top 3 options
            legs = flight_option.get("flights", [])
            segments = []
            for leg in legs:
                segments.append({
                    "airline": leg.get("airline", "Unknown"),
                    "flight_number": leg.get("flight_number", "N/A"),
                    "departure_time": leg.get("departure_airport", {}).get("time", "N/A"),
                    "arrival_time": leg.get("arrival_airport", {}).get("time", "N/A"),
                    "duration": leg.get("duration", "N/A"),
                })
            flight_info.append({
                "segments": segments,
                "price": flight_option.get("price", "N/A"),
                "total_duration": flight_option.get("total_duration", "N/A")
            })

        return {"flights": flight_info, "origin": origin, "destination": destination, "date": date}

    except Exception as e:
        return {"error": f"Failed to fetch flight data: {str(e)}"}



# print(get_flight_info("HOU","CDG", "2025-08-03","2025-08-10"))