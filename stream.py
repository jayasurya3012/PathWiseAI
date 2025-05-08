import streamlit as st
from openai import OpenAI
import requests
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import re

# ---------------------------
# Groq API Client
# ---------------------------
client = OpenAI(
    api_key="abcd1234",  #ADD YOUR GROQ API KEY
    base_url="https://api.groq.com/openai/v1"
)

# ---------------------------
# Detect User's City via IP
# ---------------------------
def get_user_location():
    try:
        res = requests.get("http://ip-api.com/json/").json()
        return res.get("city", "Unknown")
    except:
        return "Unknown"

# ---------------------------
# Generate Itinerary
# ---------------------------
def generate_itinerary(destination, days, interest):
    prompt = (
        f"Create a {days}-day travel itinerary for {destination} focused on {interest}. "
        f"For each day, list exactly 3 to 4 real-world places in bullet point format with 1-line descriptions. "
        f"Format strictly like:\nDay 1:\n- Place One (description)\n- Place Two (description)\n..."
    )
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": "You are a helpful travel planner."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ---------------------------
# Refine Itinerary
# ---------------------------
def refine_itinerary(original_itinerary, feedback):
    prompt = (
        f"Here is a travel itinerary:\n{original_itinerary}\n\nUser feedback: {feedback}\n"
        f"Update the itinerary accordingly with bullet format and short place descriptions."
    )
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": "You are a helpful travel planner."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ---------------------------
# Parse itinerary into dict
# ---------------------------
def parse_itinerary(text):
    route_dict = {}
    current_day = None
    for line in text.splitlines():
        line = line.strip()
        day_match = re.match(r"(?i)^day\s*\d+", line)
        if day_match:
            current_day = day_match.group()
            route_dict[current_day] = []
        elif line.startswith("-") and current_day:
            place = line[1:].strip()
            if place:
                route_dict[current_day].append(place)
    return route_dict

# ---------------------------
# Build Google Maps Link
# ---------------------------
def build_directions_link(places, destination):
    encoded = [quote_plus(f"{p} {destination}") for p in places]
    return f"https://www.google.com/maps/dir/" + "/".join(encoded)

# ---------------------------
# Cost Estimator Agent
# ---------------------------
def estimate_cost(itinerary_text, destination, days, interest):
    prompt = (
        f"Break down the estimated travel costs in USD per day for the following itinerary to {destination} "
        f"for {days} days, focused on {interest}. For each day, give estimated costs for: accommodation, food, entry fees, local transport. "
        f"At the end, include a total cost for the entire trip. Format strictly like:\n"
        f"Day 1:\n- Accommodation: $xx\n- Food: $xx\n- Entry Fees: $xx\n- Transport: $xx\n- Total: $xx\n...\n"
        f"Grand Total: $XXX\n\n"
        f"Itinerary:\n{itinerary_text}"
    )
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": "You are a travel budget planner."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content




# ---------------------------
# Streamlit App
# ---------------------------
st.set_page_config(page_title="PathWiseAI", layout="wide")
st.title("🧳 PathWise.ai")

user_city = get_user_location()
st.markdown(f"📍 *Detected Location:* {user_city}")

destination = st.text_input("🌍 Destination City", "Tokyo") 
days = st.text_input("📅 Trip Duration", "3") 
interest = st.text_input("🎯 Focus Area - How this trip has to be for you...", "Culture")
departure_date = st.date_input("🛫 Departure Date", datetime.today())
return_date = departure_date + timedelta(days=int(days))
st.markdown(f"🛬 *Return Date:* {return_date.strftime('%Y-%m-%d')}")

if st.button("🧠 Generate My AI Trip"):
    with st.spinner("Planning your adventure..."):
        itinerary_text = generate_itinerary(destination, days, interest)
        st.session_state.itinerary = itinerary_text
        st.session_state.dates = (departure_date, return_date)
        st.markdown("## 📋 Itinerary")
        st.markdown(itinerary_text)
        cost_text = estimate_cost(itinerary_text, destination, days, interest)
        st.session_state.cost = cost_text
        st.subheader("💰 Estimated Costs")
        st.markdown(cost_text)

        # Flights
        dep = departure_date.strftime("%Y-%m-%d")
        ret = return_date.strftime("%Y-%m-%d")
        flights_url = f"https://www.google.com/travel/flights?q=Flights+from+{quote_plus(user_city)}+to+{quote_plus(destination)}+on+{dep}+returning+on+{ret}"
        st.subheader("✈️ Flights")
        st.markdown(f"[🔗 Flights from {user_city} to {destination}]({flights_url})", unsafe_allow_html=True)

        # Destination route
        route = f"https://www.google.com/maps/dir/{quote_plus(user_city)}/{quote_plus(destination)}"
        st.subheader("🚗 General Route")
        st.markdown(f"[📍 Route to {destination}]({route})", unsafe_allow_html=True)

        # Daily Plans
        st.subheader("🗺️ Day-by-Day Route Maps")
        routes = parse_itinerary(itinerary_text)
        for day, places in routes.items():
            st.markdown(f"### {day}")
            for p in places:
                st.markdown(f"- {p}")
            if len(places) >= 2:
                maps_link = build_directions_link(places, destination)
                st.markdown(f"[🧭 View Route for {day}]({maps_link})", unsafe_allow_html=True)

# Feedback update
if "itinerary" in st.session_state:
    st.subheader("💬 Refine Itinerary")
    feedback = st.text_area("Adjust your trip (e.g., add rest on Day 2, more food places):")
    if st.button("🔁 Update Itinerary"):
        with st.spinner("Revising your plan..."):
            updated = refine_itinerary(st.session_state.itinerary, feedback)
            st.session_state.itinerary = updated
            st.markdown("## ✨ Updated Itinerary")
            st.markdown(updated)

            dep, ret = st.session_state.dates
            dep_str = dep.strftime("%Y-%m-%d")
            ret_str = ret.strftime("%Y-%m-%d")
            flights_url = (
                f"https://www.google.com/travel/flights?q=Flights+from+{quote_plus(user_city)}"
                f"+to+{quote_plus(destination)}+on+{dep_str}+returning+on+{ret_str}"
            )
            st.subheader("✈️ Flights Again")
            st.markdown(f"[🔗 Flights Link]({flights_url})", unsafe_allow_html=True)

            st.subheader("🗺️ Refined Daily Routes")
            routes = parse_itinerary(updated)
            for day, places in routes.items():
                st.markdown(f"### {day}")
                for p in places:
                    st.markdown(f"- {p}")
                # Ensure that maps are displayed after refining the itinerary
                if len(places) >= 2:
                    maps_link = build_directions_link(places, destination)
                    st.markdown(f"[🧭 View Route for {day}]({maps_link})", unsafe_allow_html=True)
