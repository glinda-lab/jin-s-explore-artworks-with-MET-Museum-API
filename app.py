# app.py
import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import math

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

st.set_page_config(page_title="MET Artwork Browser", layout="wide")

st.title("MET 컬렉션 브라우저")
st.markdown("MET Museum Collection API를 사용한 간단한 스트림릿 갤러리 예제")

# --- Sidebar
st.sidebar.header("검색 & 옵션")
query = st.sidebar.text_input("검색어 (예: sunflowers, Monet, 19th century)", value="sunflower")
only_with_images = st.sidebar.checkbox("이미지 있는 것만", value=True)
per_page = st.sidebar.selectbox("한 페이지에 표시", [12, 24, 36], index=1)

if st.sidebar.button("검색"):
    st.session_state['query_changed'] = True

# Use session_state to store results and current page
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'total' not in st.session_state:
    st.session_state['total'] = 0
if 'page' not in st.session_state:
    st.session_state['page'] = 1

def met_search(q, hasImages=True):
    params = {"q": q}
    if hasImages:
        params['hasImages'] = 'true'
    r = requests.get(f"{API_BASE}/search", params=params, timeout=10)
    r.raise_for_status()
    return r.json()  # contains total and objectIDs

def get_object(obj_id):
    r = requests.get(f"{API_BASE}/objects/{obj_id}", timeout=10)
    r.raise_for_status()
    return r.json()

# Trigger search when query changed or first load
if st.session_state.get('query_changed', False) or st.session_state['results'] == []:
    try:
        with st.spinner("MET에서 검색 중..."):
            res = met_search(query, only_with_images)
            ids = res.get('objectIDs') or []
            st.session_state['total'] = res.get('total', 0)
            st.session_state['results'] = ids
            st.session_state['page'] = 1
            st.session_state['query_changed'] = False
    except Exception as e:
        st.error(f"검색 실패: {e}")

# Pagination controls
total = st.session_state['total']
ids = st.session_state['results']
if total == 0:
    st.info("검색결과가 없습니다. 다른 검색어를 시도해 보세요.")
else:
    pages = math.ceil(len(ids) / per_page)
    left_col, mid_col, right_col = st.columns([1,4,1])
    with left_col:
        if st.button("이전") and st.session_state['page'] > 1:
            st.session_state['page'] -= 1
    with right_col:
        if st.button("다음") and st.session_state['page'] < pages:
            st.session_state['page'] += 1
    with mid_col:
        st.markdown(f"**총 {total}건 — 페이지 {st.session_state['page']} / {pages}**")

    # show grid
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
        except Exception as e:
            img_url = None
            title = f"Error loading {obj_id}"
            artist = ""
            year = ""

        col = cols[i % 4]
        with col:
            if img_url:
                try:
                    resp = requests.get(img_url, timeout=10)
                    img = Image.open(BytesIO(resp.content))
                    st.image(img, use_column_width=True)
                except:
                    st.text("이미지 로드 실패")
            else:
                st.text("이미지 없음")

            st.caption(f"**{title}**\n{artist} · {year}")
            if st.button(f"상세보기: {obj_id}", key=f"detail_{obj_id}"):
                st.session_state['selected'] = obj_id

# 상세 보기 모달(사이드 혹은 하단)
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
                resp = requests.get(img_url, timeout=10)
                img = Image.open(BytesIO(resp.content))
                st.image(img, use_column_width=True)
            else:
                st.text("이미지 없음")
        with cols[1]:
            st.markdown(f"**작가:** {meta.get('artistDisplayName','-')}")
            st.markdown(f"**제작연도:** {meta.get('objectDate','-')}")
            st.markdown(f"**소장처:** {meta.get('repository','-')}")
            st.markdown(f"**재료/기법:** {meta.get('medium','-')}")
            st.markdown(f"**분류:** {meta.get('classification','-')}")
            if meta.get('creditLine'):
                st.markdown(f"**출처:** {meta.get('creditLine')}")
            if meta.get('objectURL'):
                st.markdown(f"[MET 페이지로 이동]({meta.get('objectURL')})")
            if st.button("닫기"):
                del st.session_state['selected']
    except Exception as e:
        st.error(f"상세 불러오기 실패: {e}")
        if st.button("닫기 에러"):
            del st.session_state['selected']
