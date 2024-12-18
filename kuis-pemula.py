import streamlit as st
import streamlit_authenticator as stauth
import random
import json
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(
    page_title="Kuis Pemula", 
    page_icon="https://www.unud.ac.id/upload/images/logo%20unud%20%282%29%281%29.png"
)

# Load dari Firestore Database
firebase_credentials = dict(st.secrets["firebase"])

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def load_cookie_config():
    try:
        cookie_ref = db.collection("cookies").document("default_cookie")
        cookie = cookie_ref.get()
        
        if cookie.exists:
            return cookie.to_dict()
        else:
            st.error("Cookie configuration not found!")
            return None
        
    except Exception as e:
        st.error(f"Error loading cookie configuration: {e}")
        return None
    
def load_user_credentials():
    try:
        users_ref = db.collection("users")
        docs = users_ref.stream()
        credentials = {"usernames": {}}
        
        for doc in docs:
            user_data = doc.to_dict()
            credentials["usernames"][doc.id] = {
                "email": user_data["email"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "password": user_data["password"],
                "score": user_data["score"]
            }
        return credentials
    
    except Exception as e:
        st.error(f"Error loading user credentials: {e}")
        return None
    
def load_questions():
    try:
        questions_ref = db.collection("questions")
        docs = questions_ref.stream()
        questions = {}
        
        for doc in docs:
            question_data = doc.to_dict()
            questions[doc.id] = {
                "question": doc.id,
                "code": question_data.get("code", ""),
                "options": question_data.get("options", []),
                "correct_answer": question_data.get("answer", "")
            }
        return questions
        
    except Exception as e:
        st.error(f"Error loading questions: {e}")
        return None

cookie_config = load_cookie_config()
user_credentials = load_user_credentials()

if cookie_config and user_credentials:
    authenticator = stauth.Authenticate(
        user_credentials,
        cookie_config['name'],
        cookie_config['key'],
        cookie_config['expiry_days']
    )


# Login and Main Page
def auth():
    # Login page/form
    try:
        authenticator.login()
        st.markdown("""
                    <style>
                        div.stButton > button:first-child {
                            display: block;
                            margin: 0 auto;
                            width: 100%;
                            text-align: center;
                            padding: 10px;
                        }
                    </style>
                    """, unsafe_allow_html=True)
        
        if st.session_state['authentication_status']:
            # Main Page
            st.title("Kuis Pemula")
            st.markdown(f"Selamat Datang **{st.session_state["name"]}**!")

            if st.button("Mulai"):
                st.session_state.page = "quiz_page"
                st.rerun()
                
            if st.button("Leaderboard"):
                st.session_state.page = "leaderboard_page"
                st.rerun()
                
            authenticator.logout()
            
        elif st.session_state['authentication_status'] is False:
            if st.button("Register"):
                st.session_state.page = "register_page"
                st.rerun()
            st.error('Invalid username or password')
            
        elif st.session_state['authentication_status'] is None:
            if st.button("Register"):
                st.session_state.page = "register_page"
                st.rerun()
            st.warning('Please enter your username and password')

    except Exception as e:
        st.error(e)


#Register Page
def register_page():
    # Register form
    with st.form("register"):
        st.subheader("Register")
        
        cols1 = st.columns(2)
        with cols1[0]:
            first_name = st.text_input("Firts Name")
        with cols1[1]:
            last_name = st.text_input("Last Name")
        
        username = st.text_input("Username")
        
        cols2 = st.columns(2)
        with cols2[0]:
            password = st.text_input("Password", type="password")
        with cols2[1]:
            pw = st.text_input("Repeat Password", type="password")
        
        if st.form_submit_button("Register"):
            if first_name and last_name and username and password and pw:
                if password == pw:
                    try:
                        email = f"{first_name.lower()}{last_name.lower()}@kuispemula.com"
                        hashed_password = stauth.Hasher.hash(password)
                        
                        db.collection("users").document(username).set({
                            "email": email,
                            "first_name": first_name.split()[0],
                            "last_name": last_name.split()[-1],
                            "password": hashed_password,
                            "score": 0
                        })
                        
                        st.success("Registration successful! You can now log in.")
                    
                    except Exception as e:
                        st.error(e)
                else:
                    st.error("Passwords do not match")
            else:
                st.error("Please fill in all fields")
                
    st.markdown("""
                <style>
                    div.stButton > button:first-child {
                        display: block;
                        margin: 0 auto;
                        width: 100%;
                        text-align: center;
                        padding: 10px;
                    }
                </style>
                """, unsafe_allow_html=True)
    
    if st.button("Login"):
        st.session_state.page = "auth"
        st.rerun()


# Leaderboard Page
def leaderboard_page():
    st.title("Leaderboard")
    st.markdown("""___""")
    st.markdown("""
                <style>
                    div.stButton > button:first-child {
                        display: block;
                        margin: 0 auto;
                        width: 100%;
                        text-align: center;
                        padding: 10px;
                    }
                </style>
                """, unsafe_allow_html=True)
    
    try:
        lead_ref = db.collection("users")
        leaderboard_data = []
        
        for doc in lead_ref.stream():
            lead = doc.to_dict()
            leaderboard_data.append({
                "Name": lead["first_name"],
                "Score": lead.get("score", 0)
            })
        
        sorted_leaderboard = sorted(leaderboard_data, key=lambda x: x["Score"], reverse=True)
        
        for i, entry in enumerate(sorted_leaderboard[:10], start=1):
            st.subheader(f"**#{i} {entry['Name']}** - Score: {entry['Score']}")
            st.markdown("""___""")
    
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat leaderboard: {e}")
    
    if st.button("Kembali"):
        st.session_state.page = "auth"
        st.rerun()

        
# Quiz Page
def quiz_page():
    if 'quiz_data' not in st.session_state:
        quiz_data = load_questions()
        
        if not quiz_data:
            st.error("Tidak dapat memuat soal. Silakan coba lagi nanti.")
            return
            
        st.session_state.quiz_data = random.sample(list(quiz_data.values()), min(len(quiz_data), 10))
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.selected_option = None
        st.session_state.answer_submitted = False
        
    question_item = st.session_state.quiz_data[st.session_state.current_index]
    
    st.write(f"Pertanyaan {st.session_state.current_index + 1}")
    st.subheader(question_item['question'])
    st.subheader(question_item['code'])
    
    st.markdown(""" ___""")
    
    options = question_item['options']
    correct_answer = question_item['correct_answer']

    st.markdown("""
                <style>
                    div.stButton > button:first-child {
                        display: block;
                        margin: 0 auto;
                        width: 100%;
                        text-align: center;
                        padding: 10px;
                    }
                </style>
                """, unsafe_allow_html=True)
        
    if st.session_state.answer_submitted:
        for option in options:
            if option == correct_answer:
                st.success(f"{option} (Correct answer)")
            elif option == st.session_state.selected_option:
                st.error(f"{option} (Incorrect answer)")
    else:
        cols = st.columns(2)
        
        for i, option in enumerate(options):
            with cols[i % 2]:
                if st.button(option):
                    st.session_state.selected_option = option
                    submit_answer()
                
    st.markdown(""" ___""")
    
    if st.session_state.answer_submitted:
        if st.session_state.current_index < len(st.session_state.quiz_data) - 1:
            st.button('Next', on_click=lambda: next_question())
        else:
            st.write(f"Quiz completed! Your score is: {st.session_state.score} / {len(st.session_state.quiz_data) * 10}")
            
            update_user_score(st.session_state.score)
            
            if st.button("Selesai"):
                st.session_state.page = "auth"
                restart_quiz()
                st.rerun()

# Fungsi submit jawaban
def submit_answer():
    if st.session_state.selected_option is not None:
        st.session_state.answer_submitted = True
        
        if st.session_state.selected_option == st.session_state.quiz_data[st.session_state.current_index]['correct_answer']:
            st.session_state.score += 10
            
        st.rerun()
    else:
        st.warning("Tolong pilih jawaban.")
        
def next_question():
    st.session_state.current_index += 1
    st.session_state.selected_option = None
    st.session_state.answer_submitted = False
    
def restart_quiz():
    quiz_data = load_questions()
    st.session_state.quiz_data = random.sample(list(quiz_data.values()), min(len(quiz_data), 10))
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.selected_option = None
    st.session_state.answer_submitted = False
    
def update_user_score(score):
    try:
        user_id = st.session_state["username"]
        
        if not user_id:
            st.warning("User tidak terdeteksi. Skor tidak bisa diperbarui.")
            return

        user_ref = db.collection("users").document(user_id)
        user_data = user_ref.get()

        if user_data.exists:
            current_score = user_data.to_dict().get("score", 0)
            new_score = current_score + score
            user_ref.update({"score": new_score})
            st.success(f"Skor berhasil diperbarui!")
        else:
            st.error("Data pengguna tidak ditemukan.")
    
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memperbarui skor: {e}")


# App Runner
if 'page' not in st.session_state:
    st.session_state.page = "auth"

if cookie_config and user_credentials:
    if st.session_state.page == "auth":
        auth()
    elif st.session_state.page == "register_page":
        register_page()
    elif st.session_state.page == "leaderboard_page":
        leaderboard_page()
    elif st.session_state.page == "quiz_page":
        quiz_page()
