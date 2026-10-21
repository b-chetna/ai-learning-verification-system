import streamlit as st
import pandas as pd

from database import get_connection
from quiz import show_student_quizzes

def get_student_subjects(student_id):
    conn = get_connection()

    subjects = conn.execute("""
        SELECT s.id, s.name
        FROM subjects s
        JOIN student_subjects ss ON ss.subject_id = s.id
        WHERE ss.student_id = ?
          AND s.is_active = 1
        ORDER BY s.name
    """, (student_id,)).fetchall()

    conn.close()
    return [dict(subject) for subject in subjects]


def get_student_stats(student_id):
    conn = get_connection()

    stats = conn.execute("""
        SELECT
            COUNT(*) AS attempted,
            AVG(100.0 * score / NULLIF(max_score, 0)) AS average_score
        FROM quiz_attempts
        WHERE student_id = ?
          AND status = 'Submitted'
          AND max_score > 0
    """, (student_id,)).fetchone()

    conn.close()
    return dict(stats)


def get_class_rank(student_id, class_name, subject_id=None):
    if not class_name:
        return None, None

    conn = get_connection()

    query = """
        SELECT
            u.id,
            AVG(100.0 * a.score / NULLIF(a.max_score, 0)) AS average_score
        FROM users u
        JOIN quiz_attempts a ON a.student_id = u.id
        JOIN quizzes q ON q.id = a.quiz_id
        WHERE u.role = 'Student'
          AND u.class_name = ?
          AND a.status = 'Submitted'
          AND a.max_score > 0
    """

    params = [class_name]

    if subject_id is not None:
        query += " AND q.subject_id = ?"
        params.append(subject_id)

    query += " GROUP BY u.id ORDER BY average_score DESC"

    students = conn.execute(query, params).fetchall()
    conn.close()

    if not students:
        return None, None

    for rank, student in enumerate(students, start=1):
        if student["id"] == student_id:
            return rank, len(students)

    return None, len(students)


def get_upcoming_quizzes(student_id):
    conn = get_connection()

    quizzes = conn.execute("""
        SELECT q.id, q.title, q.scheduled_at, q.due_at, s.name AS subject
        FROM quizzes q
        JOIN subjects s ON s.id = q.subject_id
        JOIN student_subjects ss
            ON ss.subject_id = q.subject_id
           AND ss.student_id = ?
        WHERE q.status = 'Published'
          AND q.scheduled_at IS NOT NULL
          AND datetime(q.scheduled_at) >= datetime('now')
        ORDER BY datetime(q.scheduled_at)
    """, (student_id,)).fetchall()

    conn.close()
    return [dict(quiz) for quiz in quizzes]


def get_quiz_history(student_id, subject_id):
    conn = get_connection()

    quizzes = conn.execute("""
        SELECT
            q.id AS quiz_id,
            q.title,
            q.scheduled_at,
            q.due_at,
            a.status AS attempt_status,
            a.score,
            a.max_score,
            a.submitted_at,
            a.started_at
        FROM quizzes q
        LEFT JOIN quiz_attempts a ON a.id = (
            SELECT a2.id
            FROM quiz_attempts a2
            WHERE a2.quiz_id = q.id
              AND a2.student_id = ?
            ORDER BY a2.started_at DESC, a2.id DESC
            LIMIT 1
        )
        WHERE q.subject_id = ?
          AND q.status = 'Published'
        ORDER BY q.id DESC
    """, (student_id, subject_id)).fetchall()

    conn.close()
    return [dict(quiz) for quiz in quizzes]


def get_topic_performance(student_id, subject_id):
    conn = get_connection()

    topics = conn.execute("""
        SELECT
            t.id,
            t.name,
            COUNT(aa.id) AS questions_answered,
            COALESCE(SUM(aa.is_correct), 0) AS correct_answers,
            COALESCE(SUM(aa.help_used), 0) AS help_count
        FROM topics t
        JOIN questions q ON q.topic_id = t.id
        JOIN quizzes z ON z.id = q.quiz_id
        JOIN quiz_attempts a ON a.quiz_id = z.id
        JOIN attempt_answers aa
            ON aa.attempt_id = a.id
           AND aa.question_id = q.id
        WHERE a.student_id = ?
          AND z.subject_id = ?
          AND a.status = 'Submitted'
        GROUP BY t.id, t.name
        ORDER BY t.name
    """, (student_id, subject_id)).fetchall()

    conn.close()

    results = []

    for topic in topics:
        topic = dict(topic)

        total = topic["questions_answered"]
        correct = topic["correct_answers"]

        accuracy = (correct / total) * 100 if total else 0

        if accuracy >= 80:
            level = "Strong"
        elif accuracy >= 50:
            level = "Moderate"
        else:
            level = "Weak"

        topic["accuracy"] = round(accuracy, 1)
        topic["level"] = level

        results.append(topic)

    return results


def request_requiz(student_id, quiz_id):
    conn = get_connection()

    # Check for an existing pending request
    existing = conn.execute("""
        SELECT id
        FROM requiz_requests
        WHERE student_id = ?
          AND quiz_id = ?
          AND status = 'Pending'
    """, (student_id, quiz_id)).fetchone()

    if existing:
        conn.close()
        return False

    # Get quiz and teacher details
    quiz = conn.execute("""
        SELECT q.title, q.teacher_id, u.full_name AS student_name
        FROM quizzes q
        JOIN users u ON u.id = ?
        WHERE q.id = ?
    """, (student_id, quiz_id)).fetchone()

    if not quiz:
        conn.close()
        return False

    # Save the request
    cursor = conn.execute("""
        INSERT INTO requiz_requests
        (student_id, quiz_id, reason)
        VALUES (?, ?, ?)
    """, (student_id, quiz_id, "Student requested a re-quiz"))

    request_id = cursor.lastrowid

    # Count all requests for this student and quiz
    count = conn.execute("""
        SELECT COUNT(*)
        FROM requiz_requests
        WHERE student_id = ?
          AND quiz_id = ?
    """, (student_id, quiz_id)).fetchone()[0]

    # Notify the teacher
    message = (
        f"{quiz['student_name']} has requested a re-quiz "
        f"for '{quiz['title']}' {count} time(s)."
    )

    conn.execute("""
        INSERT INTO notifications (
            recipient_id,
            notification_type,
            message,
            reference_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        quiz["teacher_id"],
        "requiz_request",
        message,
        request_id
    ))

    conn.commit()
    conn.close()
    return True

def show_student_dashboard(user):
    student_id = user["id"]

    st.markdown(
        """
        <style>
        .student-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        div[data-testid="stMetric"] {
            padding: 14px;
            border: 1px solid rgba(128,128,128,0.25);
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    header_left, header_right = st.columns([3, 1])

    with header_left:
        st.title("Student Dashboard")
        st.caption("Track your learning and improve your performance.")

    with header_right:
        st.write("")
        st.markdown(
            f"**👤 {user['full_name']}**"
        )
        st.caption(f"Class: {user.get('class_name') or 'Not assigned'}")

    subjects = get_student_subjects(student_id)
    stats = get_student_stats(student_id)

    average = stats["average_score"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Enrolled Subjects", len(subjects))

    with col2:
        st.metric("Quizzes Attempted", stats["attempted"])

    with col3:
        st.metric(
            "Average Score",
            f"{average:.1f}%" if average is not None else "—"
        )

    overall_rank, total_students = get_class_rank(
        student_id,
        user.get("class_name")
    )

    if overall_rank is not None:
        st.info(
            f"**Overall Class Rank:** {overall_rank} of {total_students}"
        )
    elif user.get("class_name"):
        st.info("Your overall class rank will appear after quiz results are available.")
    else:
        st.info("Your class rank will appear once your class is assigned.")

    st.divider()

    st.subheader("📅 Upcoming Quizzes")

    upcoming = get_upcoming_quizzes(student_id)

    if upcoming:
        upcoming_df = pd.DataFrame(upcoming)
        upcoming_df = upcoming_df.rename(columns={
            "title": "Quiz",
            "subject": "Subject",
            "scheduled_at": "Scheduled At",
            "due_at": "Due At"
        })

        st.dataframe(
            upcoming_df[["Quiz", "Subject", "Scheduled At", "Due At"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No upcoming quizzes have been published yet.")

    st.divider()

    show_student_quizzes(student_id)

    st.divider()

    st.subheader("📚 My Subjects")

    if not subjects:
        st.warning("You are not enrolled in any active subjects.")
        return

    subject_names = [subject["name"] for subject in subjects]

    selected_name = st.selectbox(
        "Choose a subject",
        subject_names,
        key="student_subject_select"
    )

    selected_subject = next(
        subject for subject in subjects
        if subject["name"] == selected_name
    )

    subject_id = selected_subject["id"]

    tab1, tab2, tab3 = st.tabs([
        "Quiz Performance",
        "Topic Analysis",
        "Class Rank"
    ])

    with tab1:
        st.subheader(f"{selected_name} — Quiz Performance")

        history = get_quiz_history(student_id, subject_id)

        if not history:
            st.info("No published quizzes are available for this subject yet.")
        else:
            rows = []

            for quiz in history:
                status = quiz["attempt_status"]

                if status == "Submitted":
                    if quiz["max_score"]:
                        score = (
                            f"{quiz['score']}/{quiz['max_score']}"
                        )
                    else:
                        score = "Submitted"

                    quiz_status = "Attempted"

                elif status == "In Progress":
                    score = "—"
                    quiz_status = "In Progress"

                else:
                    score = "—"
                    quiz_status = "Not Attempted"

                rows.append({
                    "Quiz": quiz["title"],
                    "Score": score,
                    "Status": quiz_status
                })

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Unattempted quizzes are shown as Not Attempted, "
                "not as zero marks."
            )

            st.markdown("#### Request a Re-quiz")

            for quiz in history:
                if quiz["attempt_status"] == "Submitted":
                    if st.button(
                        f"Request re-quiz: {quiz['title']}",
                        key=f"requiz_{quiz['quiz_id']}"
                    ):
                        success = request_requiz(
                            student_id,
                            quiz["quiz_id"]
                        )

                        if success:
                            st.success("Your re-quiz request has been submitted.")
                        else:
                            st.info("You already have a pending request for this quiz.")

    with tab2:
        st.subheader("Strong, Moderate and Weak Topics")

        topic_results = get_topic_performance(
            student_id,
            subject_id
        )

        if not topic_results:
            st.info(
                "Topic analysis will appear after you submit a quiz "
                "containing questions linked to topics."
            )
        else:
            for level in ["Weak", "Moderate", "Strong"]:
                matching_topics = [
                    topic for topic in topic_results
                    if topic["level"] == level
                ]

                with st.expander(
                    f"{level} Topics ({len(matching_topics)})",
                    expanded=(level == "Weak")
                ):
                    if not matching_topics:
                        st.write("No topics in this category yet.")
                    else:
                        for topic in matching_topics:
                            st.write(
                                f"**{topic['name']}** — "
                                f"{topic['accuracy']}% accuracy"
                            )

                            st.progress(
                                min(
                                    max(topic["accuracy"] / 100, 0.0),
                                    1.0
                                )
                            )

                            st.caption(
                                f"Questions answered: "
                                f"{topic['questions_answered']} | "
                                f"Correct: {topic['correct_answers']} | "
                                f"Help used: {topic['help_count']}"
                            )

    with tab3:
        st.subheader(f"{selected_name} — Class Rank")

        subject_rank, subject_total = get_class_rank(
            student_id,
            user.get("class_name"),
            subject_id
        )

        if subject_rank is not None:
            st.metric(
                "Subject Class Rank",
                f"{subject_rank} of {subject_total}"
            )
        else:
            st.info(
                "Subject rank will appear when class members "
                "have submitted quizzes for this subject."
            )