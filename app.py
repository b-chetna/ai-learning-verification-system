import streamlit as st
from database import create_database
from auth import show_login, logout
from student import show_student_dashboard
from teacher import show_teacher_dashboard
from administrator import show_administrator_dashboard

st.set_page_config(
    page_title="AI Learning Verification System",
    page_icon="🎓",
    layout="wide"
)

create_database()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user" not in st.session_state:
    st.session_state["user"] = None

def show_parent_dashboard():
    st.title("👨‍👩‍👧 Parent Dashboard")
    st.write("Monitor your child's academic progress.")

    st.subheader("Student Performance")
    st.info("Subject-wise marks, class ranks, and teacher messaging will be implemented next.")


if not st.session_state["logged_in"]:
    show_login()

else:
    user = st.session_state["user"]

    with st.sidebar:
        st.title("🎓 Learning Verification")
        st.write(f"**User:** {user['full_name']}")
        st.write(f"**Role:** {user['role']}")
        st.divider()

        if st.button("Logout", use_container_width=True):
            logout()

    if user["role"] == "Student":
        show_student_dashboard(user)

    elif user["role"] == "Teacher":
        show_teacher_dashboard(user)

    elif user["role"] == "Administrator":
        show_administrator_dashboard(user)

    elif user["role"] == "Parent":
        show_parent_dashboard()