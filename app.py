import streamlit as st
import itertools
import urllib.parse
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- Page Setup ---
st.set_page_config(page_title="Route Optimizer", page_icon="🚚")
st.title("🚚 Delivery Route Optimizer")

# --- State Management ---
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

# --- UI: Add New Stop (Inside a Form for auto-clearing) ---
st.subheader("➕ Add a New Stop")

# 'clear_on_submit=True' is the magic part you asked for!
with st.form("my_form", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        name = st.text_input("Customer Name", placeholder="e.g. Itamar")
    with col_b:
        phone = st.text_input("Phone (Optional)", placeholder="050-XXXXXXX")

    addr = st.text_input("Address", placeholder="Street, City, Israel")

    # In a form, you MUST use st.form_submit_button
    submitted = st.form_submit_button("Add Stop to Route", use_container_width=True)
    
    if submitted:
        if addr:
            st.session_state.deliveries.append({
                "name": name if name else "Customer", 
                "address": addr, 
                "phone": phone
            })
            st.rerun()
        else:
            st.warning("Please enter an address!")

st.divider()
# Putting Name and Phone side-by-side to save vertical space
col_a, col_b = st.columns(2)
with col_a:
    name = st.text_input("Customer Name", placeholder="e.g. Itamar")
with col_b:
    phone = st.text_input("Phone (Optional)", placeholder="050-XXXXXXX")

addr = st.text_input("Address", placeholder="Street, City, Israel")

# Separate, prominent button
if st.button("Add Stop to Route", use_container_width=True):
    if addr:
        st.session_state.deliveries.append({
            "name": name if name else "Customer", 
            "address": addr, 
            "phone": phone
        })
        st.rerun()
    else:
        st.warning("Please enter an address!")

st.divider() # Adds a nice line to separate input from the list

# --- UI: Current List ---
st.subheader("Current Stops")
if not st.session_state.deliveries:
    st.info("Your list is empty. Add some stops above!")
else:
    for i, stop in enumerate(st.session_state.deliveries):
        # Adjusted column ratios for better mobile viewing
        cols = st.columns([0.4, 0.2, 0.2, 0.2])
        
        cols[0].write(f"**{i+1}. {stop['name']}**")
        cols[0].caption(stop['address']) # Address sits neatly under the name
        
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
if st.button("🚀 Optimize & Route", type="primary", use_container_width=True):
    if not st.session_state.deliveries:
        st.error("Add some stops first!")
    else:
        with st.spinner("Finding the best path..."):
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
            
            # Updated Google Maps URL format for better reliability
            dest = urllib.parse.quote(optimized_route[-1]['address'])
            waypoints = "%7C".join([urllib.parse.quote(d['address']) for d in optimized_route[:-1]])
            origin = urllib.parse.quote(start_addr)
            maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&waypoints={waypoints}"
            
            st.link_button("🗺️ Open Full Route in Maps", maps_url, use_container_width=True)
