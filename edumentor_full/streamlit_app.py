import os
import requests
import streamlit as st
from datetime import datetime
import io
import json

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="EduMentor AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# Kaggle-inspired theme
st.markdown("""
<style>
    /* Main container - clean white background */
    .main {
        background-color: #ffffff;
    }
    
    /* Sidebar - light blue/gray theme like Kaggle */
    [data-testid="stSidebar"] {
        background-color: #f7f9fa;
        border-right: 1px solid #e0e5e8;
    }
    
    /* Sidebar text styling */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #2c3e50 !important;
        font-weight: 500;
    }
    
    /* Sidebar inputs - clean white with subtle borders */
    [data-testid="stSidebar"] .stTextInput>div>div>input,
    [data-testid="stSidebar"] .stNumberInput>div>div>input {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #d1d8dd;
        border-radius: 4px;
        padding: 8px 12px;
    }
    
    [data-testid="stSidebar"] .stTextInput>div>div>input:focus,
    [data-testid="stSidebar"] .stNumberInput>div>div>input:focus {
        border-color: #20beff;
        box-shadow: 0 0 0 1px #20beff;
    }
    
    /* Sidebar selectbox */
    [data-testid="stSidebar"] .stSelectbox>div>div>div {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #d1d8dd;
        border-radius: 4px;
    }
    
    /* Profile header - Kaggle blue accent */
    [data-testid="stSidebar"] h1 {
        color: #20beff !important;
        font-weight: 600;
    }
    
    /* Main headers - Kaggle blue */
    h1, h2, h3 {
        color: #20beff !important;
        font-weight: 600;
    }
    
    /* Subheadings */
    .stMarkdown h2, .stMarkdown h3 {
        color: #2c3e50 !important;
        font-weight: 600;
    }
    
    /* Main screen input fields - white with subtle borders */
    .stTextInput>div>div>input {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #d1d8dd;
        border-radius: 4px;
        padding: 8px 12px;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #20beff;
        box-shadow: 0 0 0 1px #20beff;
    }
    
    .stNumberInput>div>div>input {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #d1d8dd;
        border-radius: 4px;
    }
    
    /* Selectbox main screen - Kaggle style */
    .stSelectbox>div>div>div {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #d1d8dd;
        border-radius: 4px;
    }
    
    .stSelectbox>div>div>div:hover {
        border-color: #20beff;
    }
    
    /* Buttons - Kaggle blue primary button */
    .stButton>button {
        background-color: #20beff;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #1a9fd6;
    }
    
    /* Form submit button */
    .stFormSubmitButton>button {
        background-color: #20beff;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }
    
    .stFormSubmitButton>button:hover {
        background-color: #1a9fd6;
    }
    
    /* Chat messages styling */
    .stMarkdown p {
        color: #2c3e50;
        line-height: 1.6;
    }
    
    /* Info box styling - light blue like Kaggle */
    .stAlert {
        background-color: #e8f4fd;
        color: #2c3e50;
        border-left: 4px solid #20beff;
        border-radius: 4px;
    }
    
    /* Caption text */
    .css-10trblm, [data-testid="stCaptionContainer"] {
        color: #6c757d;
    }
    
    /* Labels */
    label {
        color: #2c3e50 !important;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables first
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "subject" not in st.session_state:
    st.session_state.subject = "maths"

if "db_history" not in st.session_state:
    st.session_state.db_history = []

if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = []

if "quiz_start_time" not in st.session_state:
    st.session_state.quiz_start_time = None

if "quiz_results" not in st.session_state:
    st.session_state.quiz_results = None

# Create layout with single main content column
main_col = st.container()

with main_col:
    st.title("🎓 EduMentor AI")
    st.caption("An Intelligent Multi-Agent Learning Companion")


# Load persisted profile for demo_user on startup
def load_profile():
    try:
        resp = requests.get(f"{BACKEND_URL}/profile/demo_user", timeout=5)
        if resp.status_code == 200:
            st.session_state.profile = resp.json() or {}
    except Exception:
        # ignore network errors on startup
        pass


# Load chat history from database
def load_chat_history():
    try:
        resp = requests.get(f"{BACKEND_URL}/chat-history/demo_user?limit=20", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.db_history = data.get("history", [])
    except Exception:
        pass


load_profile()
load_chat_history()

with main_col:
    # Subject selector on main screen
    col1, col2 = st.columns([3, 1])
    with col1:
        subject = st.selectbox("Select Subject", ["maths", "science", "evs"], key="subject_selector")
        st.session_state.subject = subject
    with col2:
        st.markdown('<style>div.row-widget.stButton > button {font-size: 14px; padding: 0.25rem 0.75rem;}</style>', unsafe_allow_html=True)
        if st.button("📚 Manage Docs"):
            st.session_state.show_upload = not st.session_state.get("show_upload", False)

with main_col:
    # PDF Upload Section
    if st.session_state.get("show_upload", False):
        with st.expander("📤 Upload PDF Documents", expanded=True):
            st.markdown(f"**Upload PDF for: {st.session_state.subject.upper()}**")
            
            st.info("ℹ️ **Note**: PDFs must contain text (not scanned images). "
                    "If upload fails, your PDF might be image-based. Convert it using OCR first.")
            
            uploaded_file = st.file_uploader(
                f"Choose a PDF file for {st.session_state.subject}",
                type=["pdf"],
                key=f"pdf_uploader_{st.session_state.subject}"
            )
            
            col_upload, col_stats = st.columns(2)
            
            with col_upload:
                if uploaded_file is not None:
                    if st.button("Upload to Vector Store"):
                        with st.spinner("Processing PDF..."):
                            try:
                                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                                resp = requests.post(
                                    f"{BACKEND_URL}/upload-pdf/{st.session_state.subject}",
                                    files=files,
                                    timeout=60
                                )
                                resp.raise_for_status()
                                result = resp.json()
                                st.success(f"✅ Uploaded {result['filename']}: {result['chunks_added']} chunks added")
                            except Exception as e:
                                st.error(f"Failed to upload: {e}")
            
            with col_stats:
                # Show subject statistics
                try:
                    resp = requests.get(f"{BACKEND_URL}/subject-stats/{st.session_state.subject}", timeout=5)
                    if resp.status_code == 200:
                        stats = resp.json()
                        st.info(f"**Documents in {st.session_state.subject}:**\n\n"
                               f"📄 Total chunks: {stats['document_count']}\n\n"
                               f"📚 Sources: {len(stats['sources'])}")
                        if stats['sources']:
                            with st.expander("View sources"):
                                for src in stats['sources']:
                                    st.text(f"• {src}")
                except Exception:
                    pass

with main_col:
    with st.form(key="chat_form", clear_on_submit=True):
        user_message = st.text_input("Ask EduMentor a question or request a study plan:")
        submitted = st.form_submit_button("Send")

    if submitted and user_message:
        try:
            payload = {
                "user_id": "demo_user",
                "message": user_message,
                "session_id": st.session_state.session_id,
                "subject": st.session_state.subject,
            }
            resp = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            st.session_state.session_id = data["session_id"]
            reply = data["reply"]
            st.session_state.chat_history.append(("You", user_message))
            st.session_state.chat_history.append(("EduMentor", reply))
            # Reload history after new message
            load_chat_history()
        except Exception as e:
            st.error(f"Error contacting backend: {e}")

with main_col:
    st.markdown("---")
    st.subheader("Current Conversation")
    
    if not st.session_state.chat_history:
        st.info(
            "Try asking: `Solve 2x + 3 = 11 step by step` or "
            "`Create a study plan for my algebra test in 5 days`."
        )
    else:
        # Display messages in reverse order (most recent Q&A pair first)
        # Chat history is stored as pairs: [("You", question), ("EduMentor", answer), ...]
        num_pairs = len(st.session_state.chat_history) // 2
        
        for pair_idx in range(num_pairs - 1, -1, -1):
            q_idx = pair_idx * 2
            a_idx = q_idx + 1
            
            # Display question
            if q_idx < len(st.session_state.chat_history):
                speaker, text = st.session_state.chat_history[q_idx]
                st.markdown(f"**🧑 You:** {text}")
            
            # Display answer
            if a_idx < len(st.session_state.chat_history):
                speaker, text = st.session_state.chat_history[a_idx]
                st.markdown(f"**🤖 EduMentor:** {text}")
            
            # Add separator between Q&A pairs (except after the last one)
            if pair_idx > 0:
                st.markdown("---")


# Profile sidebar with nested sections
with st.sidebar:
    with st.expander("👤 Student Profile", expanded=True):
        with st.form(key="profile_form"):
            name = st.text_input("Name", value=st.session_state.profile.get("name", ""))
            # Ensure default age is a valid int >= min_value (1)
            stored_age = st.session_state.profile.get("age")
            try:
                default_age = int(stored_age) if stored_age is not None else 1
            except Exception:
                default_age = 1
            if default_age < 1:
                default_age = 1
            age = st.number_input("Age", min_value=1, max_value=120, value=default_age)
            class_field = st.text_input("Grade", value=st.session_state.profile.get("grade", ""))
            syllabus = st.text_input("Syllabus", value=st.session_state.profile.get("syllabus", ""))
            proficiency = st.selectbox("Proficiency", ["beginner", "intermediate", "advanced"], index={"beginner":0,"intermediate":1,"advanced":2}.get(st.session_state.profile.get("proficiency","beginner"),0))
            gender = st.selectbox("Gender", ["male","female","other"], index={"male":0,"female":1,"other":2}.get(st.session_state.profile.get("gender","male"),0))
            save_profile = st.form_submit_button("Save Profile")

            if save_profile:
                # Basic client-side validation before sending
                if not class_field or not class_field.strip():
                    st.error("Grade cannot be empty")
                else:
                    payload = {
                        "name": name,
                        "age": age,
                        "grade_field": class_field,
                        "syllabus": syllabus,
                        "proficiency": proficiency,
                        "gender": gender,
                    }
                    try:
                        resp = requests.post(f"{BACKEND_URL}/profile/demo_user", json=payload, timeout=10)
                        resp.raise_for_status()
                        st.success("Profile saved")
                        st.session_state.profile = resp.json()
                    except requests.exceptions.HTTPError as http_err:
                        # surface validation errors returned by the server
                        try:
                            detail = resp.json()
                        except Exception:
                            detail = str(http_err)
                        st.error(f"Failed to save profile: {detail}")
                    except Exception as e:
                        st.error(f"Failed to save profile: {e}")
    
    # History section in sidebar
    with st.expander("📜 History", expanded=False):
        # Filter options
        history_filter = st.selectbox("Filter by:", ["All Subjects", "maths", "science", "evs"], key="history_filter_sidebar")
        
        col_refresh, col_clear = st.columns(2)
        with col_refresh:
            if st.button("🔄", use_container_width=True, key="refresh_sidebar"):
                load_chat_history()
                st.rerun()
        
        with col_clear:
            if st.button("🗑️", use_container_width=True, key="clear_sidebar"):
                try:
                    resp = requests.delete(f"{BACKEND_URL}/chat-history/demo_user", timeout=5)
                    if resp.status_code == 200:
                        st.success("History cleared!")
                        st.session_state.db_history = []
                        load_chat_history()
                except Exception as e:
                    st.error(f"Failed to clear history: {e}")
        
        st.markdown("---")
        
        # Display history from database
        if not st.session_state.db_history:
            st.info("No history yet. Start chatting!")
        else:
            filtered_history = st.session_state.db_history
            if history_filter != "All Subjects":
                filtered_history = [h for h in st.session_state.db_history if h.get('subject') == history_filter]
            
            for idx, item in enumerate(filtered_history[:10]):  # Show latest 10 in sidebar
                with st.expander(f"💬 {item['question'][:35]}...", expanded=False):
                    st.caption(f"{item.get('subject', 'N/A').upper()} • {item['timestamp'][:16]}")
                    st.markdown("**🧑 You:**")
                    st.markdown(item['question'])
                    st.markdown("**🤖 EduMentor:**")
                    st.markdown(item['answer'])
                st.markdown("")  # Small spacing
    
    # Quiz section in sidebar
    with st.expander("📝 Quiz", expanded=False):
        if not st.session_state.quiz_active and not st.session_state.quiz_results:
            # Quiz setup form
            with st.form(key="quiz_setup_form_sidebar"):
                st.markdown("**Test your knowledge!**")
                quiz_subject = st.selectbox("Subject", ["maths", "science", "evs"], key="quiz_subject_selector_sidebar")
                quiz_topic = st.text_input("Topic", placeholder="e.g., Algebra")
                quiz_difficulty = st.selectbox("Difficulty", ["beginner", "intermediate", "advanced"], key="diff_sidebar")
                num_questions = st.number_input("Questions", min_value=3, max_value=10, value=5, key="num_sidebar")
                
                start_quiz = st.form_submit_button("🚀 Start Quiz")
            
            if start_quiz and quiz_topic and quiz_subject:
                with st.spinner("Generating quiz..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/quiz/generate",
                            json={
                                "user_id": "demo_user",
                                "subject": quiz_subject,
                                "topic": quiz_topic,
                                "difficulty": quiz_difficulty,
                                "num_questions": num_questions
                            },
                            timeout=90
                        )
                        resp.raise_for_status()
                        quiz_data = resp.json()
                        st.session_state.quiz_data = quiz_data
                        st.session_state.quiz_active = True
                        st.session_state.quiz_answers = [-1] * len(quiz_data["questions"])
                        st.session_state.quiz_start_time = datetime.now()
                        st.rerun()
                    except requests.exceptions.Timeout:
                        st.error("Quiz generation timed out. Please try again.")
                    except Exception as e:
                        st.error(f"Failed to generate quiz: {e}")
            elif start_quiz:
                st.warning("Please enter a topic")
        
        elif st.session_state.quiz_active and st.session_state.quiz_data:
            st.info("Quiz in progress! Check the main area.")
            if st.button("Cancel Quiz", use_container_width=True, key="cancel_sidebar"):
                st.session_state.quiz_active = False
                st.session_state.quiz_data = None
                st.session_state.quiz_answers = []
                st.rerun()
        
        elif st.session_state.quiz_results:
            results = st.session_state.quiz_results
            st.success(f"Score: {results['score_percentage']:.1f}%")
            st.markdown(f"**{results['correct_answers']}/{results['total_questions']} correct**")
            if st.button("New Quiz", use_container_width=True, key="new_sidebar"):
                st.session_state.quiz_results = None
                st.session_state.quiz_data = None
                st.session_state.quiz_answers = []
                st.rerun()

# Main content area
# History and Quiz are now in the sidebar

# Handle quiz display in main area if quiz is active
with main_col:
    if st.session_state.quiz_active:
        # Display quiz questions
        quiz_data = st.session_state.quiz_data
        st.markdown(f"### 📝 Quiz: {quiz_data['topic'].title()}")
        st.markdown(f"**Subject:** {quiz_data['subject'].upper()} | **Difficulty:** {quiz_data['difficulty'].title()}")
        st.markdown("---")
        
        # Display questions
        for i, q in enumerate(quiz_data["questions"]):
            st.markdown(f"**Question {i+1}:** {q['question']}")
            answer = st.radio(
                "Select your answer:",
                options=range(len(q["options"])),
                format_func=lambda x, i=i: f"{chr(65+x)}. {quiz_data['questions'][i]['options'][x]}",
                key=f"quiz_q_{i}",
                index=st.session_state.quiz_answers[i] if st.session_state.quiz_answers[i] != -1 else 0
            )
            st.session_state.quiz_answers[i] = answer
            st.markdown("---")
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            if st.button("✅ Submit Quiz", use_container_width=True):
                time_taken = (datetime.now() - st.session_state.quiz_start_time).total_seconds()
                
                with st.spinner("Submitting..."):
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/quiz/submit",
                            json={
                                "user_id": "demo_user",
                                "result_id": quiz_data["result_id"],
                                "answers": st.session_state.quiz_answers,
                                "time_taken_seconds": int(time_taken)
                            },
                            timeout=10
                        )
                        resp.raise_for_status()
                        results = resp.json()
                        st.session_state.quiz_results = results
                        st.session_state.quiz_active = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit quiz: {e}")
        
        with col_cancel:
            if st.button("❌ Cancel Quiz", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.quiz_data = None
                st.session_state.quiz_answers = []
                st.rerun()
    
    elif st.session_state.quiz_results:
            # Display results
            results = st.session_state.quiz_results
            
            # Score display
            score_pct = results["score_percentage"]
            if score_pct >= 80:
                st.success(f"🎉 Excellent! You scored {score_pct}%")
            elif score_pct >= 60:
                st.info(f"👍 Good job! You scored {score_pct}%")
            else:
                st.warning(f"📚 You scored {score_pct}%. Keep practicing!")
            
            st.markdown(f"**Score:** {results['correct_answers']}/{results['total_questions']} correct")
            st.markdown(f"**Status:** {'✅ Passed' if results['passed'] else '❌ Need More Practice'}")
            st.markdown("---")
            
            # Detailed results
            st.markdown("### Detailed Results")
            for i, item in enumerate(results["detailed_results"]):
                with st.expander(f"Question {i+1}: {'✅ Correct' if item['is_correct'] else '❌ Wrong'}"):
                    st.markdown(f"**Q:** {item['question']}")
                    st.markdown(f"**Your Answer:** {chr(65+item['user_answer']) if item['user_answer'] is not None else 'Not answered'}. {item['options'][item['user_answer']] if item['user_answer'] is not None else ''}")
                    st.markdown(f"**Correct Answer:** {chr(65+item['correct_answer'])}. {item['options'][item['correct_answer']]}")
                    st.markdown(f"**Explanation:** {item['explanation']}")
            
            # Download results button
            def generate_report():
                report = f"""Quiz Results - EduMentor AI
================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Subject: {st.session_state.quiz_data['subject'].upper()}
Topic: {st.session_state.quiz_data['topic']}
Difficulty: {st.session_state.quiz_data['difficulty'].title()}

Score: {results['correct_answers']}/{results['total_questions']} ({score_pct}%)
Status: {'PASSED' if results['passed'] else 'NEEDS IMPROVEMENT'}

================================
DETAILED RESULTS
================================

"""
                for i, item in enumerate(results["detailed_results"]):
                    report += f"""
Question {i+1}: {'✓ CORRECT' if item['is_correct'] else '✗ WRONG'}
Q: {item['question']}
Your Answer: {chr(65+item['user_answer']) if item['user_answer'] is not None else 'Not answered'}. {item['options'][item['user_answer']] if item['user_answer'] is not None else ''}
Correct Answer: {chr(65+item['correct_answer'])}. {item['options'][item['correct_answer']]}
Explanation: {item['explanation']}

---
"""
                return report
            
            # Download PDF button
            # Get student name from profile or use default
            student_name = st.session_state.get("name", "Student")
            
            # Generate PDF download URL
            pdf_url = f"{BACKEND_URL}/quiz/download/{results['result_id']}?student_name={student_name}"
            
            if st.button("📥 Download PDF", use_container_width=True):
                try:
                    resp = requests.get(pdf_url, timeout=30)
                    if resp.status_code == 200:
                        st.download_button(
                            label="💾 Save PDF",
                            data=resp.content,
                            file_name=f"quiz_results_{st.session_state.quiz_data['subject']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="pdf_save"
                        )
                    else:
                        st.error(f"Failed to generate PDF: {resp.status_code}")
                except Exception as e:
                    st.error(f"Failed to download PDF: {e}")
            
            st.markdown("---")
            col_new, col_view = st.columns(2)
            with col_new:
                if st.button("🆕 Take Another Quiz", use_container_width=True):
                    st.session_state.quiz_results = None
                    st.session_state.quiz_data = None
                    st.session_state.quiz_answers = []
                    st.rerun()
            
            with col_view:
                if st.button("📊 View Statistics", use_container_width=True):
                    try:
                        resp = requests.get(f"{BACKEND_URL}/quiz/statistics/demo_user", timeout=5)
                        if resp.status_code == 200:
                            stats = resp.json()
                            st.markdown("### Your Quiz Statistics")
                            st.markdown(f"- **Total Quizzes:** {stats['total_quizzes']}")
                            st.markdown(f"- **Average Score:** {stats['average_score']}%")
                            st.markdown(f"- **Best Score:** {stats['best_score']}%")
                            st.markdown(f"- **Total Questions Answered:** {stats['total_questions_answered']}")
                            
                            if stats['by_subject']:
                                st.markdown("**By Subject:**")
                                for subj in stats['by_subject']:
                                    st.markdown(f"  - {subj['subject'].upper()}: {subj['quiz_count']} quizzes, {subj['avg_score']}% avg")
                    except Exception as e:
                        st.error(f"Failed to load statistics: {e}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6c757d; padding: 10px;'>"
    "© 2025 Edumentor. All rights reserved."
    "</div>",
    unsafe_allow_html=True
)
