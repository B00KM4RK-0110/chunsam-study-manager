import streamlit as st
import pyrebase
import PyPDF2
import google.generativeai as genai
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

# 구글 캘린더 연동 부품
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

# ==========================================
# 🔑 1. 개인 설정 (Firebase & Gemini)
# ==========================================
firebaseConfig = {
    "apiKey": "AIzaSyB6ldiUhVfbjdru4fg1Vw34_uy2o8x24Dg",
    "authDomain": "chunsam-study-manager.firebaseapp.com",
    "projectId": "chunsam-study-manager",
    "storageBucket": "chunsam-study-manager.firebasestorage.app",
    "messagingSenderId": "675000940925",
    "appId": "1:675000940925:web:0656282b342dab017a3414",
    "databaseURL": "" 
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# --- 🔐 구글 OAuth2 설정 (슬래시 없는 주소 적용) ---
GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
# Secrets에 저장된 주소도 끝에 /가 없어야 합니다.
GOOGLE_REDIRECT_URI = st.secrets["GOOGLE_REDIRECT_URI"]

client_config = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [GOOGLE_REDIRECT_URI]
    }
}
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

st.set_page_config(page_title="춘삼이의 스마트 학사 비서", layout="wide")

# 세션 초기화
if 'user' not in st.session_state: st.session_state.user = None
if 'my_courses' not in st.session_state: st.session_state.my_courses = {}
if 'current_view' not in st.session_state: st.session_state.current_view = "대시보드"

# --- 🔄 구글 인증 콜백 처리 ---
if "code" in st.query_params:
    try:
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
        flow.fetch_token(code=st.query_params["code"])
        st.session_state.google_creds = flow.credentials
        st.query_params.clear() 
        st.success("✅ 구글 캘린더 연동 성공!")
    except Exception as e:
        st.error(f"연동 실패: {e}")

# --- 🧠 파서 및 날짜 로직 ---
def parse_with_gemini(raw_text):
    prompt = f"강의계획서를 분석해 JSON으로 응답해. 과목명, 교수명, day_of_week(월~일), 15주차 학습내용 포함. {raw_text}"
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def get_class_dates(start_date, day_of_week_str):
    days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    target_day = days.get(day_of_week_str, 0)
    diff = (target_day - start_date.weekday()) % 7
    first_date = start_date + timedelta(days=diff)
    return [(first_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(15)]

# --- 🖥️ 메인 UI ---
if st.session_state.user is None:
    st.title("🎓 춘삼 스터디 매니저 접속")
    email = st.text_input("이메일")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인", type="primary"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.user = user
            st.rerun()
        except: st.error("로그인 실패")
else:
    st.sidebar.title("📚 나의 캠퍼스")
    if st.sidebar.button("➕ 새 강의 등록", use_container_width=True): st.session_state.current_view = "강의등록"
    
    for c_name in st.session_state.my_courses.keys():
        if st.sidebar.button(f"📅 {c_name} 캘린더", key=f"side_{c_name}"):
            st.session_state.current_view = f"calendar_{c_name}"

    if st.session_state.current_view == "강의등록":
        st.header("✨ 강의 분석")
        start_dt = st.date_input("학기 시작일(월요일)", datetime(2026, 3, 2))
        file = st.file_uploader("PDF 업로드", type=['pdf'])
        if file and st.button("분석 시작"):
            reader = PyPDF2.PdfReader(file)
            text = "".join([p.extract_text() for p in reader.pages])
            res = parse_with_gemini(text)
            dates = get_class_dates(start_dt, res.get('day_of_week', '월'))
            res['weeks'] = {f"{i+1}주차": {"date": dates[i], "content": c} for i, c in enumerate(res['weeks'].values())}
            st.session_state.my_courses[res['name']] = res
            st.rerun()

    elif st.session_state.current_view.startswith("calendar_"):
        c_name = st.session_state.current_view.replace("calendar_", "")
        data = st.session_state.my_courses[c_name]
        events = [{"title": f"[{w}] {c_name}", "start": d['date'], "end": d['date'], "resource": d['content']} for w, d in data['weeks'].items()]
        
        calendar(events=events)
        
        if st.button("🗓️ Google 캘린더 일괄 등록", type="primary"):
            if 'google_creds' not in st.session_state:
                flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.markdown(f"### [🔗 구글 계정 연동하기]({auth_url})")
            else:
                service = build('calendar', 'v3', credentials=st.session_state.google_creds)
                for e in events:
                    service.events().insert(calendarId='primary', body={'summary': e['title'], 'description': e['resource'], 'start': {'date': e['start']}, 'end': {'date': e['start']}}).execute()
                st.success("✅ 15주차 일정 등록 완료!")