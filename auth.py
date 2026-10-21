import streamlit as st
from database import login_user


def show_login():
    st.markdown("""
        <style>
        .block-container {
            max-width: 1100px;
            padding-top: 3rem;
        }

        .main-title {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .tagline {
            text-align: center;
            color: #A0A7B4;
            font-size: 1.05rem;
            margin-bottom: 40px;
        }

        .login-title {
            text-align: center;
            font-size: 1.7rem;
            font-weight: 600;
            margin-bottom: 20px;
        }

        div[data-testid="stForm"] {
            max-width: 560px;
            margin: auto;
            padding: 30px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 14px;
        }

        div[data-testid="stForm"] input {
            min-height: 48px;
        }

        div[data-testid="stForm"] div[data-baseweb="select"] > div {
            min-height: 48px;
        }

        div[data-testid="stFormSubmitButton"] {
            display: flex;
            justify-content: center;
            width: 100%;
        }

        div[data-testid="stFormSubmitButton"] button {
            width: 220px !important;
            min-width: 220px !important;
            max-width: 100% !important;
            min-height: 42px;
            white-space: nowrap !important;
            border-radius: 8px;
            font-weight: 600;
        }

        @media (max-width: 600px) {
            .block-container {
                padding: 1.5rem 1rem;
            }

            .main-title {
                font-size: 1.8rem;
            }

            .tagline {
                font-size: 0.95rem;
                margin-bottom: 28px;
            }

            div[data-testid="stForm"] {
                padding: 18px;
            }

            div[data-testid="stFormSubmitButton"] button {
                width: 180px !important;
                min-width: 180px !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="main-title">🎓 AI Learning Verification System</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="tagline">Verify learning. Identify weaknesses. Improve performance.</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="login-title">Login to Your Account</div>',
        unsafe_allow_html=True
    )

    with st.form("login_form"):
        role = st.selectbox(
            "Login as",
            ["Student", "Teacher", "Administrator", "Parent"]
        )

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

        if submitted:
            if not username.strip() or not password:
                st.error("Please enter your username and password.")
            else:
                user = login_user(username.strip(), password, role)

                if user:
                    st.session_state["user"] = user
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid username, password, or role.")


def logout():
    st.session_state["user"] = None
    st.session_state["logged_in"] = False
    st.rerun()