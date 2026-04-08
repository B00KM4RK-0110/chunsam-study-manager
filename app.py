import streamlit as st
import pyrebase
import PyPDF2
import google.generativeai as genai
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

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

# Streamlit 금고에서 키를 꺼내옵니다.
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="춘삼이의 스마트 학사 비서", layout="wide")

# 세션 초기화
if 'user' not in st.session_state: st.session_state.user = None
if 'my_courses' not in st.session_state: st.session_state.my_courses = {}
if 'current_view' not in st.session_state: st.session_state.current_view = "대시보드"

# --- 🧠 파서 함수 (요일 추출 로직 포함) ---
def parse_with_gemini(raw_text):
    prompt = f"""
    너는 대학교 학사일정 분석 전문가야. 아래 텍스트에서 정보를 추출해 JSON으로 응답해.
    1. 과목명, 교수명
    2. '강의시간' 항목을 보고 수업 요일을 파악해서 'day_of_week'에 "월", "화", "수", "목", "금", "토", "일" 중 하나로 기록해.
    3. 1~15주차별 수업 내용을 정리해.

    [JSON 형식]
    {{
        "name": "과목명",
        "prof": "교수명",
        "day_of_week": "요일",
        "exams": ["중간고사: 일정", "기말고사: 일정"],
        "weeks": {{
            "1주차": "학습 내용", "2주차": "학습 내용", "3주차": "학습 내용", "4주차": "학습 내용", "5주차": "학습 내용",
            "6주차": "학습 내용", "7주차": "학습 내용", "8주차": "학습 내용", "9주차": "학습 내용", "10주차": "학습 내용",
            "11주차": "학습 내용", "12주차": "학습 내용", "13주차": "학습 내용", "14주차": "학습 내용", "15주차": "학습 내용"
        }}
    }}
    반드시 마크다운(```json) 없이 순수 JSON 텍스트만 출력해.
    
    [강의계획서 텍스트]
    {raw_text}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        clean_text = response.text.strip()
        if clean_text.startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
http://googleusercontent.com/immersive_entry_chip/2

스트림릿 클라우드가 코드를 갱신할 때까지 약 1분 정도 기다렸다가 웹사이트를 새로고침(F5) 하시면, 반가운 학사모 아이콘과 함께 이메일 입력창이 다시 짠! 하고 나타날 것입니다. 다시 한번 혼란을 드려 미안하네! 확인 후 결과를 알려주게나.