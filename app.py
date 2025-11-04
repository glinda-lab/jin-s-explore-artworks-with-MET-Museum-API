# app.py
import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import math

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StreamlitApp/1.0; +https://streamlit.io)"}

st.set_page_config(page_title="MET Artwork Browser", layout="wide")

st.title("MET Artwork Browser")
st.markdown("A simple Streamlit gallery app powered by the MET Museum Collection API.")

# --- Sidebar
st.sidebar.header("Search & Options")
query = st.sidebar.text_input("Keyword (e.g., sunflowers, Monet, 19th century)", value="sunflower")
only_with_images = st.sidebar.checkbox("Show only items with images", value=True)
per_page = st.sidebar.selectbox("Results per page", [12, 24, 36], index=1)

if st.sidebar.button("Search"):
    st.session_state['query_changed'] = True

# Session state setup
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'total' not in st.session_state:
    st.session_state['total'] = 0
if 'page' not in st.session_state:
    st.session_state['page'] = 1

def met_search(q, hasImages=True):
    """Search artworks by keyword."""
    params = {"q": q}
    if hasImages:
        params['hasImages'] = 'true'
    r = requests.get(f"{API_BASE}/search", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

def get_object(obj_id):
    """Get artwork details by object ID."""
    r = requests.get(f"{API_BASE}/objects/{obj_id}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

# --- Perform search
if st.session_state.get('query_changed', False) or st.session_state['results'] == []:
    try:
        with st.spinner("Searching the MET Collection..."):
            res = met_search(query, only_with_images)
            ids = res.get('objectIDs') or []
            st.session_state['total'] = res.get('total', 0)
            st.session_state['results'] = ids
            st.session_state['page'] = 1
            st.session_state['query_changed'] = False
    except Exception as e:
        st.error(f"Search failed: {e}")

# --- Pagination and display
total = st.session_state['total']
ids = st.session_state['results']

if total == 0:
    st.info("No results found. Try another keyword.")
else:
    pages = math.ceil(len(ids) / per_page)
    left_col, mid_col, right_col = st.columns([1,4,1])

    with left_col:
        if st.button("Previous") and st.session_state['page'] > 1:
            st.session_state['page'] -= 1
    with right_col:
        if st.button("Next") and st.session_state['page'] < pages:
            st.session_state['page'] += 1
    with mid_col:
        st.markdown(f"**Total results:** {total} — **Page:** {st.session_state['page']} / {pages}")

    start = (st.session_state['page'] - 1) * per_page
    end = start + per_page
    page_ids = ids[start:end]

    cols = st.columns(4)
    for i, obj_id in enumerate(page_ids):
        try:
            meta = get_object(obj_id)
            img_url = meta.get('primaryImageSmall') or meta.get('primaryImage')
            title = meta.get('title', 'Untitled')
            artist = meta.get('artistDisplayName', '')
            year = meta.get('objectDate', '')
        except Exception:
            img_url = None
            title = f"Error loading {obj_id}"
            artist = ""
            year = ""

        col = cols[i % 4]
        with col:
            if img_url:
                try:
                    resp = requests.get(img_url, headers=HEADERS, timeout=10)
                    img = Image.open(BytesIO(resp.content))
                    st.image(img, use_column_width=True)
                except:
                    st.text("Image load failed")
            else:
                st.text("No image available")

            st.caption(f"**{title}**\n{artist} · {year}")
            if st.button(f"Details: {obj_id}", key=f"detail_{obj_id}"):
                st.session_state['selected'] = obj_id

# --- Detail View
if 'selected' in st.session_state:
    sel = st.session_state['selected']
    try:
        meta = get_object(sel)
        st.markdown("---")
        st.subheader(meta.get('title', ''))
        cols = st.columns([1,2])
        with cols[0]:
            img_url = meta.get('primaryImage') or meta.get('primaryImageSmall')
            if img_url:
                resp = requests.get(img_url, headers=HEADERS, timeout=10)
                img = Image.open(BytesIO(resp.content))
                st.image(img, use_column_width=True)
            else:
                st.text("No image available")
        with cols[1]:
            st.markdown(f"**Artist:** {meta.get('artistDisplayName','-')}")
            st.markdown(f"**Date:** {meta.get('objectDate','-')}")
            st.markdown(f"**Repository:** {meta.get('repository','-')}")
            st.markdown(f"**Medium:** {meta.get('medium','-')}")
            st.markdown(f"**Classification:** {meta.get('classification','-')}")
            if meta.get('creditLine'):
                st.markdown(f"**Credit Line:** {meta.get('creditLine')}")
            if meta.get('objectURL'):
                st.markdown(f"[View on MET website]({meta.get('objectURL')})")
            if st.button("Close"):
                del st.session_state['selected']
    except Exception as e:
        st.error(f"Failed to load details: {e}")
        if st.button("Close error"):
            del st.session_state['selected']
