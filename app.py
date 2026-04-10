import streamlit as st
import pandas as pd
import urllib.parse
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- הגדרות דף ---
st.set_page_config(page_title="מחשב מסלול משלוחים", page_icon="🚚", layout="centered")
st.title("🚚 מחשב מסלול משלוחים")

if 'deliveries' not in st.session_state:
    st.session_state.deliveries = []

geolocator = Nominatim(user_agent="shipping_app_v6")

# --- סרגל צד וייבוא ---
with st.sidebar:
    st.header("הגדרות וייבוא")
    start_addr = st.text_input("נקודת מוצא (בסיס)", "רעננה, ישראל")
    
    st.write("---")
    uploaded_file = st.file_uploader("העלה קובץ אקסל (שם, כתובת, טלפון)", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            # קריאת הקובץ
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # ניקוי שמות העמודות מרווחים מיותרים (חשוב מאוד!)
            df.columns = [str(c).strip() for c in df.columns]
            
            # זיהוי עמודות
            col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'Name', 'לקוח'])), None)
            col_addr = next((c for c in df.columns if any(k in c for k in ['כתובת', 'Address', 'מיקום', 'addr'])), None)
            col_phone = next((c for c in df.columns if any(k in c for k in ['טלפון', 'Phone', 'נייד'])), None)

            # הצגת דיאגנוסטיקה למשתמש (דיבגינג)
            st.info(f"מזהה עמודות: שם ({col_name}), כתובת ({col_addr})")

            if st.button("✅ ייבא נתונים"):
                if not col_addr:
                    st.error("לא מצאתי עמודה של 'כתובת' באקסל. וודא שהכותרת תקינה.")
                else:
                    count = 0
                    for _, row in df.iterrows():
                        addr_val = row[col_addr]
                        if pd.notna(addr_val):
                            # תיקון טלפון (הוספת 0)
                            raw_phone = str(row[col_phone]) if col_phone and pd.notna(row[col_phone]) else ""
                            clean_phone = raw_phone.split('.')[0].strip()
                            if clean_phone.isdigit() and len(clean_phone) == 9:
                                clean_phone = "0" + clean_phone
                            
                            st.session_state.deliveries.append({
                                "name": str(row[col_name]) if col_name else "לקוח",
                                "address": str(addr_val),
                                "phone": clean_phone
                            })
                            count += 1
                    
                    st.success(f"הצלחתי לייבא {count} רשומות!")
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ: {e}")

    st.write("---")
    if st.button("🗑️ נקה הכל"):
        st.session_state.deliveries = []
        st.rerun()

# --- הוספה ידנית ---
st.subheader("➕ הוספת עצירה ידנית")
with st.form("manual_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1: name = st.text_input("שם")
    with c2: phone = st.text_input("טלפון")
    addr = st.text_input("כתובת (רחוב ועיר)")
    if st.form_submit_button("הוסף לרשימה", use_container_width=True):
        if addr:
            st.session_state.deliveries.append({"name": name or "לקוח", "address": addr, "phone": phone})
            st.rerun()

st.divider()

# --- רשימת עצירות ---
st.subheader(f"רשימת עצירות ({len(st.session_state.deliveries)})")
for i, stop in enumerate(st.session_state.deliveries):
    cols = st.columns([0.4, 0.2, 0.2, 0.2])
    cols[0].write(f"**{i+1}. {stop['name']}**")
    cols[0].caption(stop['address'])
    
    waze_url = f"https://waze.com/ul?q={urllib.parse.quote(stop['address'])}&navigate=yes"
    cols[1].markdown(f"[🔹 Waze]({waze_url})")
    
    if stop['phone']:
        cols[2].markdown(f"[📞 חיוג](tel:{stop['phone']})")
    
    if cols[3].button("❌", key=f"del_{i}"):
        st.session_state.deliveries.pop(i)
        st.rerun()

# --- כפתור אופטימיזציה ---
if st.session_state.deliveries:
    if st.button("🚀 חשב מסלול מהיר ופתח מפה", type="primary", use_container_width=True):
        with st.spinner("מחשב... זה עשוי לקחת רגע (תלוי במספר הכתובות)"):
            start_loc = geolocator.geocode(start_addr)
            if not start_loc:
                st.error("לא הצלחתי למצוא את נקודת המוצא במפה.")
            else:
                current_coords = (start_loc.latitude, start_loc.longitude)
                unvisited = []
                for d in st.session_state.deliveries:
                    time.sleep(1.1) # מניעת חסימה
                    loc = geolocator.geocode(d['address'])
                    if loc:
                        d['coords'] = (loc.latitude, loc.longitude)
                        unvisited.append(d)
                
                if not unvisited:
                    st.warning("לא הצלחתי למצוא אף אחת מהכתובות במפה. וודא שהן כתובות נכונות.")
                else:
                    optimized = []
                    while unvisited:
                        closest = min(unvisited, key=lambda x: geodesic(current_coords, x['coords']).km)
                        optimized.append(closest)
                        current_coords = closest['coords']
                        unvisited.remove(closest)
                    
                    st.session_state.deliveries = optimized
                    
                    origin = urllib.parse.quote(start_addr)
                    dest = urllib.parse.quote(optimized[-1]['address'])
                    waypoints = "%7C".join([urllib.parse.quote(d['address']) for d in optimized[:-1]])
                    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&waypoints={waypoints}&travelmode=driving"
                    st.link_button("🗺️ פתח מסלול בגוגל מפות", maps_url, use_container_width=True)
