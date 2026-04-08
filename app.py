import streamlit as st
import pyrebase
import PyPDF2
import google.generativeai as genai
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

# 구글 캘린더 연동을 위한 필수 부품들
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

# ==========================================
# 🔑 1. 개인 설정 및 금고 열쇠
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

# --- 구글 OAuth2 설정 ---
GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
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

# --- 🔄 구글 로그인 콜백 처리 (주소창에 인증 코드가 들어왔을 때) ---
if "code" in st.query_params:
    try:
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
        flow.fetch_token(code=st.query_params["code"])
        st.session_state.google_creds = flow.credentials
        st.query_params.clear() # 주소창 깔끔하게 정리
        st.success("✅ 구글 캘린더 연동이 완료되었습니다! 이제 일정을 내보낼 수 있습니다.")
    except Exception as e:
        st.error(f"구글 연동 중 오류 발생: {e}")

# --- 🧠 파서 함수 및 날짜 계산 ---
def parse_with_gemini(raw_text):
    prompt = f"""
    너는 대학교 학사일정 분석 전문가야. 
    1. 과목명, 교수명
    2. '강의시간' 요일을 파악해 'day_of_week'에 "월","화","수","목","금","토","일" 중 하나로 기록해.
    3. 1~15주차별 수업 내용을 정리해.
    [JSON 형식]
    {{"name": "과목명", "prof": "교수명", "day_of_week": "요일", "weeks": {{"1주차": "내용", "2주차": "내용"...}}}}
    반드시 순수 JSON 텍스트만 출력해.
    {raw_text}
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def get_class_dates(start_date, day_of_week_str):
    days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    target_day = days.get(day_of_week_str, 0)
    current_day = start_date.weekday()
    diff = (target_day - current_day) % 7
    first_class_date = start_date + timedelta(days=diff)
    return [(first_class_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(15)]

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
    st.sidebar.success(f"👤 {st.session_state.user['email']}")
    if st.sidebar.button("➕ 새 강의 등록", use_container_width=True): st.session_state.current_view = "강의등록"
    st.sidebar.divider()
    
    for c_name, c_data in st.session_state.my_courses.items():
        with st.sidebar.expander(f"📘 {c_name}"):
            if st.button(f"📅 캘린더 보기", key=f"cal_{c_name}", use_container_width=True):
                st.session_state.current_view = f"calendar_{c_name}"

    if st.session_state.current_view == "강의등록":
        st.header("✨ AI 강의 계획서 분석")
        start_dt = st.date_input("학기 시작일(월요일)", datetime(2026, 3, 2))
        uploaded_file = st.file_uploader("PDF 업로드", type=['pdf'])
        
        if uploaded_file and st.button("🚀 분석 시작", type="primary"):
            with st.spinner("분석 중..."):
                reader = PyPDF2.PdfReader(uploaded_file)
                text = "".join([p.extract_text() for p in reader.pages])
                result = parse_with_gemini(text)
                
                dates = get_class_dates(start_dt, result.get('day_of_week', '월'))
                new_weeks = {}
                for i, week_key in enumerate(list(result.get('weeks', {}).keys())[:15]):
                    new_weeks[week_key] = {"date": dates[i], "content": result['weeks'][week_key]}
                result['weeks'] = new_weeks
                st.session_state.my_courses[result['name']] = result
                st.session_state.current_view = f"calendar_{result['name']}"
                st.rerun()

    elif st.session_state.current_view.startswith("calendar_"):
        c_name = st.session_state.current_view.replace("calendar_", "")
        data = st.session_state.my_courses.get(c_name, {})
        st.header(f"📅 {c_name} 학습 일정표")
        
        events = []
        for week, details in data.get('weeks', {}).items():
            events.append({"title": f"[{week}] {c_name}", "start": details['date'], "end": details['date'], "resource": details['content']})
        
        calendar(events=events, options={"headerToolbar": {"left": "prev,next", "center": "title", "right": "dayGridMonth"}})
        
        st.divider()
        # --- 🌟 대망의 구글 캘린더 내보내기 버튼 🌟 ---
        if st.button("🗓️ Google 캘린더로 내보내기 (15주차 일괄 등록)", type="primary"):
            if 'google_creds' not in st.session_state or not st.session_state.google_creds.valid:
                # 1. 권한이 없으면 구글 로그인 화면 URL 생성
                flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.warning("구글 캘린더 접근 권한이 필요합니다.")
                st.markdown(f"### [👉 여기를 클릭하여 구글 계정을 연동하세요]({auth_url})")
            else:
                # 2. 권한이 있으면 캘린더에 일정 밀어넣기
                with st.spinner("구글 캘린더에 일정을 등록하고 있습니다..."):
                    try:
                        service = build('calendar', 'v3', credentials=st.session_state.google_creds)
                        count = 0
                        for event in events:
                            cal_event = {
                                'summary': event['title'],
                                'description': event['resource'],
                                'start': {'date': event['start']},
                                'end': {'date': event['start']},
                            }
                            service.events().insert(calendarId='primary', body=cal_event).execute()
                            count += 1
                        st.success(f"🎉 성공! 구글 캘린더에 총 {count}개의 일정이 등록되었습니다.")
                    except Exception as e:
                        st.error(f"일정 등록 실패: {e}")