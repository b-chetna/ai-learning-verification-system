
import streamlit as st
import pandas as pd

from database import create_database, get_connection
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

if "view_role" not in st.session_state:
    st.session_state["view_role"] = None


def show_parent_dashboard(user):
    """Read-only dashboard for the authenticated student's records."""

    student_id = user["id"]

    st.title("👨‍👩‍👧 Parent Dashboard")
    st.write(f"Academic progress for **{user['full_name']}**")

    conn = get_connection()

    try:
        # Subject-wise performance from submitted quizzes.
        subject_rows = conn.execute("""
            SELECT
                s.name AS subject,
                COUNT(a.id) AS quizzes_completed,
                ROUND(
                    AVG(
                        100.0 * a.score / NULLIF(a.max_score, 0)
                    ),
                    1
                ) AS average_percentage
            FROM quiz_attempts a
            JOIN quizzes q ON q.id = a.quiz_id
            JOIN subjects s ON s.id = q.subject_id
            WHERE a.student_id = ?
              AND a.status = 'Submitted'
              AND q.status = 'Published'
            GROUP BY s.id, s.name
            ORDER BY s.name
        """, (student_id,)).fetchall()

        # Latest attempt for each published quiz.
        quiz_rows = conn.execute("""
            SELECT
                s.name AS subject,
                q.title AS quiz,
                a.score,
                a.max_score,
                a.status,
                a.submitted_at
            FROM quizzes q
            JOIN subjects s ON s.id = q.subject_id
            JOIN quiz_attempts a ON a.quiz_id = q.id
            WHERE a.student_id = ?
              AND a.id = (
                  SELECT a2.id
                  FROM quiz_attempts a2
                  WHERE a2.student_id = ?
                    AND a2.quiz_id = q.id
                  ORDER BY a2.id DESC
                  LIMIT 1
              )
              AND q.status = 'Published'
            ORDER BY s.name, q.title
        """, (student_id, student_id)).fetchall()

        # Re-quiz requests belonging to this student only.
        request_rows = conn.execute("""
            SELECT
                s.name AS subject,
                q.title AS quiz,
                r.reason,
                r.status,
                r.requested_at,
                r.teacher_remark,
                r.reviewed_at
            FROM requiz_requests r
            JOIN quizzes q ON q.id = r.quiz_id
            JOIN subjects s ON s.id = q.subject_id
            WHERE r.student_id = ?
            ORDER BY r.requested_at DESC
        """, (student_id,)).fetchall()

    finally:
        conn.close()

    # Subject-wise performance
    st.subheader("📊 Subject-wise Performance")

    if subject_rows:
        st.dataframe(
            [
                {
                    "Subject": row["subject"],
                    "Quizzes Completed": row["quizzes_completed"],
                    "Average (%)": row["average_percentage"],
                }
                for row in subject_rows
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No submitted quiz results are available yet.")

    st.divider()

    # Individual quiz marks
    st.subheader("📝 Quiz Marks")

    if quiz_rows:
        quiz_data = []

        for row in quiz_rows:
            if row["status"] == "Submitted":
                marks = f"{row['score']} / {row['max_score']}"
                percentage = (
                    round(100 * row["score"] / row["max_score"], 1)
                    if row["max_score"]
                    else None
                )
            else:
                marks = "—"
                percentage = None

            quiz_data.append({
                "Subject": row["subject"],
                "Quiz": row["quiz"],
                "Marks": marks,
                "Percentage": (
                    f"{percentage}%"
                    if percentage is not None
                    else "—"
                ),
                "Status": row["status"],
                "Submitted At": row["submitted_at"] or "—",
            })

        st.dataframe(
            pd.DataFrame(quiz_data),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No quiz attempts are available yet.")

    st.divider()

    # Re-quiz requests
    st.subheader("🔄 Re-quiz Requests")

    if request_rows:
        st.dataframe(
            [
                {
                    "Subject": row["subject"],
                    "Quiz": row["quiz"],
                    "Reason": row["reason"] or "—",
                    "Status": row["status"],
                    "Teacher Remark": row["teacher_remark"] or "—",
                    "Requested At": row["requested_at"] or "—",
                    "Reviewed At": row["reviewed_at"] or "—",
                }
                for row in request_rows
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No re-quiz requests have been made.")

    st.caption("Parent view is read-only.")


# Login screen
if not st.session_state["logged_in"]:
    show_login()

else:
    user = st.session_state["user"]
    view_role = st.session_state.get("view_role") or user["role"]

    with st.sidebar:
        st.title("🎓 Learning Verification")
        st.write(f"**User:** {user['full_name']}")
        st.write(f"**Account Role:** {user['role']}")
        st.write(f"**Current View:** {view_role}")
        st.divider()

        if st.button("Logout", use_container_width=True):
            logout()

    # Only allow the selected view that matches the authenticated account.
    if view_role == "Student" and user["role"] == "Student":
        show_student_dashboard(user)

    elif view_role == "Parent" and user["role"] == "Student":
        show_parent_dashboard(user)

    elif view_role == "Teacher" and user["role"] == "Teacher":
        show_teacher_dashboard(user)

    elif (
        view_role == "Administrator"
        and user["role"] == "Administrator"
    ):
        show_administrator_dashboard(user)

    else:
        st.error("Your selected view does not match your account role.")
        st.session_state["logged_in"] = False
        st.session_state["user"] = None
        st.session_state["view_role"] = None
        st.rerun()
