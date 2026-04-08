import streamlit as st
import itertools
import urllib.parse
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- Page Setup ---
st.set_page_config(page_title="Route Optimizer", page_icon="🚚")
st.title("🚚 Delivery Route Optimizer")

# --- State Management (To keep data between clicks) ---
if 'deliveries' not in st.session_state:
    st.session_state.deliveries = []

geolocator = Nominatim(user_agent="shipping_app_v1")

# --- UI: Sidebar Settings ---
with st.sidebar:
    st.header("Settings")
    start_addr = st.text_input("Start/Base Address", "Ra'anana, Israel")
    if st.button("🗑️ Clear All"):
        st.session_state.deliveries = []
        st.rerun()

# --- UI: Add New Stop ---
with st.expander("➕ Add a New Stop", expanded=True):
    name = st.text_input("Customer Name")
    addr = st.text_input("Address")
    phone = st.text_input("Phone (Optional)")
    if st.button("Add Stop"):
        if addr:
            st.session_state.deliveries.append({"name": name, "address": addr, "phone": phone})
            st.rerun()

# --- UI: Current List ---
st.subheader("Current Stops")
for i, stop in enumerate(st.session_state.deliveries):
    cols = st.columns([0.5, 0.2, 0.2, 0.1])
    cols[0].write(f"**{i+1}. {stop['name']}** - {stop['address']}")
    
    # Waze Link
    waze_url = f"https://waze.com/ul?q={urllib.parse.quote(stop['address'])}&navigate=yes"
    cols[1].markdown(f"[🔹 Waze]({waze_url})")
    
    # Call Link
    if stop['phone']:
        cols[2].markdown(f"[📞 Call](tel:{stop['phone']})")
    
    # Delete
    if cols[3].button("❌", key=f"del_{i}"):
        st.session_state.deliveries.pop(i)
        st.rerun()

# --- Optimization Logic ---
if st.button("🚀 Optimize & Route", type="primary"):
    if not st.session_state.deliveries:
        st.error("Add some stops first!")
    else:
        with st.spinner("Finding the best path..."):
            # Simple Nearest Neighbor logic for the web version
            start_loc = geolocator.geocode(start_addr)
            time.sleep(1)
            current_coords = (start_loc.latitude, start_loc.longitude)
            
            unvisited = []
            for d in st.session_state.deliveries:
                loc = geolocator.geocode(d['address'])
                time.sleep(1.1)
                if loc:
                    d['coords'] = (loc.latitude, loc.longitude)
                    unvisited.append(d)
            
            optimized_route = []
            while unvisited:
                closest = min(unvisited, key=lambda x: geodesic(current_coords, x['coords']).km)
                optimized_route.append(closest)
                current_coords = closest['coords']
                unvisited.remove(closest)
            
            st.session_state.deliveries = optimized_route
            st.success("Route Optimized!")
            
            # Create Google Maps Link
            dest = urllib.parse.quote(optimized_route[-1]['address'])
            waypoints = "%7C".join([urllib.parse.quote(d['address']) for d in optimized_route[:-1]])
            maps_url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(start_addr)}&destination={dest}&waypoints={waypoints}"
            st.link_button("🗺️ Open Full Route in Maps", maps_url)