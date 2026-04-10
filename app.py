import streamlit as st
import pandas as pd
import urllib.parse
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- Page Setup ---
st.set_page_config(page_title="מחשב מסלול משלוחים", page_icon="🚚", layout="centered")
st.title("🚚 מחשב מסלול משלוחים")

# --- State Management ---
if 'deliveries' not in st.session_state:
    st.session_state.deliveries = []

geolocator = Nominatim(user_agent="shipping_app_v5")

# --- UI: Sidebar & Excel Import ---
with st.sidebar:
    st.header("הגדרות וייבוא")
    start_addr = st.text_input("נקודת מוצא (בסיס)", "רעננה, ישראל")
    
    st.write("---")
    st.subheader("ייבוא מאקסל / CSV")
    uploaded_file = st.file_uploader("העלה קובץ משלוחים", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # הצגת תצוגה מקדימה קטנה כדי לוודא שהקובץ נקרא נכון
            st.write("נמצאו נתונים בקובץ. לחץ על הכפתור למטה לייבוא:")
            
            if st.button("✅ ייבא את כל הרשימה", use_container_width=True):
                new_stops = []
                for _, row in df.iterrows():
                    # חיפוש עמודות - לוגיקה חזקה יותר
                    d_name = next((row[c] for c in df.columns if any(k in str(c).lower() for k in ['name', 'שם', 'לקוח'])), "לקוח")
                    d_addr = next((row[c] for c in df.columns if any(k in str(c).lower() for k in ['addr', 'כתובת', 'מיקום'])), None)
                    d_phone = next((row[c] for c in df.columns if any(k in str(c).lower() for k in ['phone', 'טלפון', 'נייד'])), "")
                    
                    if d_addr and str(d_addr) != 'nan':
                        # תיקון טלפון - הוספת 0 אם הוא חסר (כמו בתמונה שלך)
                        phone_str = str(d_phone).split('.')[0] # ניקוי נקודה עשרונית אם יש
                        if phone_str.isdigit() and len(phone_str) == 9:
                            phone_str = "0" + phone_str
                            
                        new_stops.append({
                            "name": str(d_name), 
                            "address": str(d_addr), 
                            "phone": phone_str
                        })
                
                st.session_state.deliveries.extend(new_stops)
                st.success(f"נוספו {len(new_stops)} עצירות!")
                st.rerun()
        except Exception as e:
            st.error(f"שגיאה: {e}")

    st.write("---")
    if st.button("🗑️ נקה את כל הרשימה"):
        st.session_state.deliveries = []
        st.rerun()

# --- UI: Add New Stop (Manual) ---
st.subheader("➕ הוספת עצירה ידנית")
with st.form("stop_input_form", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        name = st.text_input("שם הלקוח", placeholder="לדוגמה: איתמר")
    with col_b:
        phone = st.text_input("טלפון (אופציונלי)", placeholder="050-XXXXXXX")
    addr = st.text_input("כתובת מלאה", placeholder="רחוב, עיר, ישראל")
    if st.form_submit_button("הוסף לרשימה", use_container_width=True):
        if addr:
            st.session_state.deliveries.append({"name": name if name else "לקוח", "address": addr, "phone": phone})
            st.rerun()

st.divider()

# --- UI: Current List ---
st.subheader("רשימת עצירות")
if not st.session_state.deliveries:
    st.info("הרשימה ריקה. העלה אקסל או הזן כתובת.")
else:
    for i, stop in enumerate(st.session_state.deliveries):
        cols = st.columns([0.4, 0.2, 0.2, 0.2])
        cols[0].write(f"**{i+1}. {stop['name']}**")
        cols[0].caption(stop['address'])
        
        waze_url = f"https://waze.com/ul?q={urllib.parse.quote(stop['address'])}&navigate=yes"
        cols[1].markdown(f"[🔹 Waze]({waze_url})")
        
        if stop['phone'] and str(stop['phone']) not in ['nan', '']:
            cols[2].markdown(f"[📞 חיוג](tel:{stop['phone']})")
        
        if cols[3].button("❌", key=f"del_{i}"):
            st.session_state.deliveries.pop(i)
            st.rerun()

    # הכפתור החשוב ביותר
    if st.button("🚀 בצע אופטימיזציה ופתח מפה", type="primary", use_container_width=True):
        with st.spinner("מחשב מסלול..."):
            start_loc = geolocator.geocode(start_addr)
            if start_loc:
                current_coords = (start_loc.latitude, start_loc.longitude)
                unvisited = []
                for d in st.session_state.deliveries:
                    time.sleep(1.1) # חובה כדי לא להיחסם ע"י שירות המפות
                    loc = geolocator.geocode(d['address'])
                    if loc:
                        d['coords'] = (loc.latitude, loc.longitude)
                        unvisited.append(d)
                
                # Nearest Neighbor Logic
                optimized = []
                while unvisited:
                    closest = min(unvisited, key=lambda x: geodesic(current_coords, x['coords']).km)
                    optimized.append(closest)
                    current_coords = closest['coords']
                    unvisited.remove(closest)
                
                st.session_state.deliveries = optimized
                
                dest = urllib.parse.quote(optimized[-1]['address'])
                waypoints = "%7C".join([urllib.parse.quote(d['address']) for d in optimized[:-1]])
                maps_url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(start_addr)}&destination={dest}&waypoints={waypoints}&travelmode=driving"
                st.link_button("🗺️ פתח מסלול בגוגל מפות", maps_url, use_container_width=True)
