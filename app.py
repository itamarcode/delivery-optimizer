import streamlit as st
import itertools
import urllib.parse
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- Page Setup ---
st.set_page_config(page_title="Route Optimizer", page_icon="🚚", layout="centered")
st.title("🚚 Delivery Route Optimizer")

# --- State Management ---
if 'deliveries' not in st.session_state:
    st.session_state.deliveries = []

# Initialize Geocoder
geolocator = Nominatim(user_agent="shipping_app_v2")

# --- UI: Sidebar Settings ---
with st.sidebar:
    st.header("Settings")
    start_addr = st.text_input("Start/Base Address", "Ra'anana, Israel")
    if st.button("🗑️ Clear Entire Route"):
        st.session_state.deliveries = []
        st.rerun()

# --- UI: Add New Stop (Auto-Clearing Form) ---
st.subheader("➕ Add a New Stop")

# 'clear_on_submit=True' ensures the boxes wipe clean after you hit 'Add Stop'
with st.form("stop_input_form", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        name = st.text_input("Customer Name", placeholder="e.g. Itamar")
    with col_b:
        phone = st.text_input("Phone (Optional)", placeholder="050-XXXXXXX")

    addr = st.text_input("Address", placeholder="Street, City, Israel")

    # The submit button for the form
    add_pressed = st.form_submit_button("Add Stop to Route", use_container_width=True)
    
    if add_pressed:
        if addr:
            # Add to list and refresh the UI
            st.session_state.deliveries.append({
                "name": name if name else "Customer", 
                "address": addr, 
                "phone": phone
            })
            st.rerun()
        else:
            st.warning("Please enter an address before adding!")

st.divider()

# --- UI: Current List ---
st.subheader("Current Stops")

if not st.session_state.deliveries:
    st.info("Your list is empty. Type an address above to get started.")
else:
    for i, stop in enumerate(st.session_state.deliveries):
        # Column setup optimized for mobile thumbs
        cols = st.columns([0.4, 0.2, 0.2, 0.2])
        
        # Column 1: Info
        cols[0].write(f"**{i+1}. {stop['name']}**")
        cols[0].caption(stop['address'])
        
        # Column 2: Waze
        waze_url = f"https://waze.com/ul?q={urllib.parse.quote(stop['address'])}&navigate=yes"
        cols[1].markdown(f"[🔹 Waze]({waze_url})")
        
        # Column 3: Call
        if stop['phone']:
            cols[2].markdown(f"[📞 Call](tel:{stop['phone']})")
        else:
            cols[2].write("—")
        
        # Column 4: Delete
        if cols[3].button("❌", key=f"del_{i}"):
            st.session_state.deliveries.pop(i)
            st.rerun()

    st.write("---")

    # --- Optimization Logic ---
    if st.button("🚀 Optimize & Open Google Maps", type="primary", use_container_width=True):
        with st.spinner("Calculating the fastest path..."):
            # 1. Geocode the Start Point
            start_loc = geolocator.geocode(start_addr)
            time.sleep(1) # Respecting OpenStreetMap's usage policy
            
            if not start_loc:
                st.error("Could not find the Base Address. Check your spelling!")
            else:
                current_coords = (start_loc.latitude, start_loc.longitude)
                
                # 2. Geocode all stops
                unvisited = []
                for d in st.session_state.deliveries:
                    loc = geolocator.geocode(d['address'])
                    time.sleep(1.1)
                    if loc:
                        d['coords'] = (loc.latitude, loc.longitude)
                        unvisited.append(d)
                
                # 3. Simple Nearest Neighbor Algorithm
                optimized_route = []
                while unvisited:
                    closest = min(unvisited, key=lambda x: geodesic(current_coords, x['coords']).km)
                    optimized_route.append(closest)
                    current_coords = closest['coords']
                    unvisited.remove(closest)
                
                # 4. Save the new order
                st.session_state.deliveries = optimized_route
                st.success("Route Sorted by Distance!")
                
                # 5. Build the Google Maps URL
                origin = urllib.parse.quote(start_addr)
                dest = urllib.parse.quote(optimized_route[-1]['address'])
                waypoints = "%7C".join([urllib.parse.quote(d['address']) for d in optimized_route[:-1]])
                
                # This format opens directly in the Google Maps App
                maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&waypoints={waypoints}&travelmode=driving"
                
                st.link_button("🗺️ Launch Full Route", maps_url, use_container_width=True)
