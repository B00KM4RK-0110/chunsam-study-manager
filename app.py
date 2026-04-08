import streamlit as st
import pyrebase
import PyPDF2
import google.generativeai as genai
import json

# ==========================================
# 🔑 1. 개인 설정 (본인의 키를 입력하세요!)
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

# 🚨 발급받은 Gemini API 키를 넣으세요!
GEMINI_API_KEY = "AIzaSyBKFYiLhgexK2oFYwBjtfIFYUTqi2kiBAk"
# ==========================================

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="춘삼이의 스마트 학사 비서", layout="wide")

# 세션 초기화 (Syntax 에러 방지를 위해 줄바꿈 엄격 적용)
if 'user' not in st.session_state:
    st.session_state.user = None
if 'my_courses' not in st.session_state:
    st.session_state.my_courses = {}
if 'current_view' not in st.session_state:
    st.session_state.current_view = "대시보드"

# --- 🧠 정밀 타격: 제미나이 프롬프트 엔지니어링 ---
def parse_with_gemini(raw_text):
    prompt = f"""
    너는 대학교 학사일정 분석 전문가야. 아래 강의계획서 텍스트를 읽고, 
    주차별 '기간'과 '수업내용 및 학습활동' 표 데이터를 완벽하게 분석해서 JSON으로 출력해.
    
    [요구 JSON 형식]
    {{
        "name": "과목명",
        "prof": "담당교수 이름 (없으면 '미지정')",
        "exams": ["중간고사: 일정", "기말고사: 일정"],
        "weeks": {{
            "1주차": "[기간] 학습 내용",
            "2주차": "[기간] 학습 내용",
            "3주차": "[기간] 학습 내용",
            "4주차": "[기간] 학습 내용",
            "5주차": "[기간] 학습 내용",
            "6주차": "[기간] 학습 내용",
            "7주차": "[기간] 학습 내용",
            "8주차": "[기간] 학습 내용",
            "9주차": "[기간] 학습 내용",
            "10주차": "[기간] 학습 내용",
            "11주차": "[기간] 학습 내용",
            "12주차": "[기간] 학습 내용",
            "13주차": "[기간] 학습 내용",
            "14주차": "[기간] 학습 내용",
            "15주차": "[기간] 학습 내용"
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
        
        # 💡 [문법 수정] 한 줄짜리 if문을 여러 줄로 풀어 Syntax 에러 원천 차단
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        clean_json = clean_text.strip()
        return json.loads(clean_json)
        
    except Exception as e:
        # 💡 [문법 수정] 응답 객체 누락 시 발생하는 에러 방어 코드 추가
        error_msg = f"분석 오류: {str(e)}"
        if 'response' in locals():
            try:
                error_msg += f"\n\n답변 원본: {response.text}"
            except:
                pass
        return {"error": error_msg}

# --- 🖥️ 화면 UI ---
if st.session_state.user is None:
    st.title("🎓 춘삼 스터디 매니저 접속")
    email = st.text_input("이메일")
    password = st.text_input("비밀번호", type="password")
    
    if st.button("로그인", type="primary"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.user = user
            st.rerun()
        except Exception as e:
            st.error(f"로그인 실패: {e}")
else:
    # --- 📚 완벽한 주차별 내비게이션 사이드바 ---
    st.sidebar.title("📚 나의 캠퍼스")
    st.sidebar.success(f"👤 {st.session_state.user['email']}")
    
    if st.sidebar.button("➕ 새 강의 등록하기", use_container_width=True):
        st.session_state.current_view = "강의등록"
    
    st.sidebar.divider()
    st.sidebar.caption("등록된 강의 목록")
    
    for course_name, course_data in st.session_state.my_courses.items():
        with st.sidebar.expander(f"📘 {course_name}", expanded=True):
            if st.button("📊 과목 요약", key=f"btn_summary_{course_name}", use_container_width=True):
                st.session_state.current_view = f"view_{course_name}_summary"
            
            selected_week = st.selectbox("주차 이동", [f"{i}주차" for i in range(1, 16)], key=f"sel_{course_name}")
            if st.button("해당 주차로 이동", key=f"go_{course_name}"):
                st.session_state.current_view = f"view_{course_name}_{selected_week}"

    st.sidebar.divider()
    if st.sidebar.button("로그아웃"):
        st.session_state.user = None
        st.rerun()

    view = st.session_state.current_view
    
    if view == "강의등록":
        st.header("✨ 제미나이 AI 강의계획서 등록")
        uploaded_file = st.file_uploader("전자회로1 등 PDF 파일을 올리세요.", type=['pdf'])
        if uploaded_file and st.button("🚀 Gemini Flash 분석 시작", type="primary"):
            with st.spinner("Gemini가 강의계획서의 표를 읽어내는 중입니다..."):
                reader = PyPDF2.PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() for page in reader.pages])
                
                result = parse_with_gemini(raw_text)
                
                if "error" not in result:
                    st.session_state.my_courses[result['name']] = result
                    st.session_state.current_view = f"view_{result['name']}_summary"
                    st.rerun()
                else:
                    st.error("🚨 분석 실패! 아래의 원인을 확인해주세요.")
                    st.code(result['error'], language="text")

    elif view.endswith("_summary"):
        course_name = view.replace("view_", "").replace("_summary", "")
        data = st.session_state.my_courses[course_name]
        
        st.header(f"📘 {course_name} (과목 요약)")
        st.info(f"👨‍🏫 담당 교수: {data.get('prof', '미지정')}")
        st.subheader("🚨 다가오는 시험")
        
        for exam in data.get('exams', []):
            st.error(exam)
            
        st.write("👈 왼쪽 사이드바에서 원하는 주차를 선택해 해당 주차의 수업 내용을 확인하고 수정하세요.")

    elif view.startswith("view_") and "주차" in view:
        parts = view.split("_")
        course_name = parts[1]
        week_num = parts[2]
        data = st.session_state.my_courses[course_name]
        
        current_content = data['weeks'].get(week_num, "등록된 내용이 없습니다.")
        
        st.header(f"📅 {course_name} - {week_num} 학습 보드")
        st.info("아래 텍스트 박스는 현재 저장된 내용입니다. 부족한 부분이 있다면 직접 고쳐 쓰고 저장하세요.")
        
        new_content = st.text_area("학습 내용 및 목표 (언제든 수정 가능)", value=current_content, height=150)
        
        if st.button(f"💾 {week_num} 내용 업데이트", type="primary"):
            st.session_state.my_courses[course_name]['weeks'][week_num] = new_content
            st.success("내용이 완벽하게 저장되었습니다!")