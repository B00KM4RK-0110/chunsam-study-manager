import streamlit as st
import pyrebase
import PyPDF2
import google.generativeai as genai
import json
from datetime import datetime, timedelta
from streamlit_calendar import calendar

# --- 🔑 개인 설정 (기존 키 유지) ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="춘삼이의 스마트 학사 비서", layout="wide")

# 세션 초기화
if 'user' not in st.session_state: st.session_state.user = None
if 'my_courses' not in st.session_state: st.session_state.my_courses = {}
if 'current_view' not in st.session_state: st.session_state.current_view = "대시보드"

# --- 🧠 2.5-flash 지능형 파서 (요일 추출 추가) ---
def parse_with_gemini(raw_text):
    prompt = f"""
    너는 학사 일정 전문가야. 아래 텍스트에서 정보를 추출해 JSON으로 응답해.
    1. 과목명, 교수명, 시험 정보
    2. '강의시간' 항목에서 수업 요일을 찾아 'day_of_week'에 "월", "화", "수", "목", "금", "토", "일" 중 하나로 기록해.
    3. 1~15주차별 수업 내용을 정리해.
    
    [JSON 형식]
    {{
        "name": "과목명",
        "prof": "교수명",
        "day_of_week": "요일", 
        "exams": [],
        "weeks": {{ "1주차": "내용", ... }}
    }}
    {raw_text}
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_json)

# --- 📅 날짜 계산 로직 ---
def get_class_dates(start_date, day_of_week_str):
    days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    target_day = days.get(day_of_week_str, 0)
    
    # 개강주에서 해당 요일 찾기
    current_day = start_date.weekday()
    diff = (target_day - current_day) % 7
    first_class_date = start_date + timedelta(days=diff)
    
    # 15주치 날짜 리스트 생성
    return [(first_class_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(15)]

# --- 🖥️ 메인 UI ---
if st.session_state.user is None:
    # (로그인 로직 생략 - 이전 코드와 동일)
    st.title("🎓 춘삼 스터디 매니저 접속")
    # ... 로그인 UI ...
else:
    st.sidebar.title("📚 춘삼이의 캠퍼스")
    
    if st.sidebar.button("➕ 새 강의 등록 (Gemini)", use_container_width=True):
        st.session_state.current_view = "강의등록"
    
    st.sidebar.divider()
    
    # 강의 목록 탐색
    for c_name, c_data in st.session_state.my_courses.items():
        with st.sidebar.expander(f"📘 {c_name}"):
            if st.button(f"📅 캘린더 보기", key=f"cal_{c_name}"):
                st.session_state.current_view = f"calendar_{c_name}"

    # --- 기능 1: 강의 등록 및 날짜 생성 ---
    if st.session_state.current_view == "강의등록":
        st.header("✨ AI 강의 계획서 분석")
        start_dt = st.date_input("올해 학기 시작일(월요일)을 선택하세요", datetime(2026, 3, 2))
        uploaded_file = st.file_uploader("PDF 업로드", type=['pdf'])
        
        if uploaded_file and st.button("🚀 분석 및 스케줄 생성"):
            reader = PyPDF2.PdfReader(uploaded_file)
            text = "".join([p.extract_text() for p in reader.pages])
            result = parse_with_gemini(text)
            
            # 날짜 자동 계산
            dates = get_class_dates(start_dt, result['day_of_week'])
            
            # 주차별 데이터에 날짜 매핑
            new_weeks = {}
            for i, (week_key, content) in enumerate(result['weeks'].items()):
                new_weeks[week_key] = {"date": dates[i], "content": content}
            
            result['weeks'] = new_weeks
            st.session_state.my_courses[result['name']] = result
            st.success(f"'{result['name']}' ({result['day_of_week']}요일 수업) 등록 완료!")

    # --- 기능 2: 캘린더 UI 화면 ---
    elif st.session_state.current_view.startswith("calendar_"):
        c_name = st.session_state.current_view.split("_")[1]
        data = st.session_state.my_courses[c_name]
        
        st.header(f"📅 {c_name} 학습 일정표")
        
        # 캘린더 이벤트 데이터 생성
        events = []
        for week, details in data['weeks'].items():
            events.append({
                "title": f"[{week}] {details['content'][:15]}...",
                "start": details['date'],
                "end": details['date'],
                "resource": details['content']
            })
        
        # 캘린더 위젯 표시
        cal_result = calendar(events=events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}})
        
        # 클릭한 날짜의 상세 내용 표시
        if "eventClick" in cal_result:
            clicked_event = cal_result["eventClick"]["event"]
            st.subheader(f"📌 {clicked_event['start']} 수업 상세")
            st.write(clicked_event['extendedProps']['resource'])
            
        # --- 기능 3: 외부 연동 버튼 ---
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗓️ Google 캘린더로 내보내기"):
                st.info("현재 개발 모드입니다. 구글 OAuth2 설정을 마치면 자동으로 연동됩니다.")
                # 실제 구현 시에는 google-api-python-client를 사용하여 이벤트를 push합니다.
        with col2:
            st.button("📝 Notion 페이지로 복사")