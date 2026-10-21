import streamlit as st
import pandas as pd

from pathlib import Path
from datetime import datetime, date, time, timedelta

from database import get_connection

def get_teacher_subjects(teacher_id):
    conn = get_connection()

    subjects = conn.execute("""
        SELECT s.id, s.name
        FROM subjects s
        JOIN teacher_subjects ts ON ts.subject_id = s.id
        WHERE ts.teacher_id = ?
          AND s.is_active = 1
        ORDER BY s.name
    """, (teacher_id,)).fetchall()

    conn.close()

    return [dict(subject) for subject in subjects]


def get_subject_topics(subject_id):
    conn = get_connection()

    topics = conn.execute("""
        SELECT id, name
        FROM topics
        WHERE subject_id = ?
        ORDER BY name
    """, (subject_id,)).fetchall()

    conn.close()

    return [dict(topic) for topic in topics]


def get_teacher_quizzes(teacher_id, subject_id):
    conn = get_connection()

    quizzes = conn.execute("""
        SELECT
            q.id,
            q.title,
            q.status,
            q.scheduled_at,
            q.due_at,
            COUNT(DISTINCT qs.id) AS question_count
        FROM quizzes q
        LEFT JOIN questions qs ON qs.quiz_id = q.id
        WHERE q.teacher_id = ?
          AND q.subject_id = ?
        GROUP BY q.id
        ORDER BY q.id DESC
    """, (teacher_id, subject_id)).fetchall()

    conn.close()

    return [dict(quiz) for quiz in quizzes]


def create_topic(subject_id, topic_name):
    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO topics (subject_id, name)
            VALUES (?, ?)
        """, (subject_id, topic_name.strip()))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def create_quiz(teacher_id, subject_id, title, description,
                scheduled_at, due_at):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO quizzes (
            subject_id,
            teacher_id,
            title,
            description,
            scheduled_at,
            due_at,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'Draft')
    """, (
        subject_id,
        teacher_id,
        title.strip(),
        description.strip(),
        scheduled_at,
        due_at
    ))

    quiz_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return quiz_id


def add_question(
    quiz_id,
    topic_id,
    question_text,
    option_a,
    option_b,
    option_c,
    option_d,
    correct_answer,
    explanation,
    difficulty,
    marks
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO questions (
            quiz_id,
            topic_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
            difficulty,
            marks
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        quiz_id,
        topic_id,
        question_text.strip(),
        option_a.strip(),
        option_b.strip(),
        option_c.strip(),
        option_d.strip(),
        correct_answer,
        explanation.strip(),
        difficulty,
        marks
    ))

    conn.commit()
    conn.close()


def get_quiz_questions(quiz_id):
    conn = get_connection()

    questions = conn.execute("""
        SELECT
            q.id,
            q.question_text,
            q.correct_answer,
            q.marks,
            q.difficulty,
            t.name AS topic
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        WHERE q.quiz_id = ?
        ORDER BY q.id
    """, (quiz_id,)).fetchall()

    conn.close()

    return [dict(question) for question in questions]


def publish_quiz(quiz_id, teacher_id):
    conn = get_connection()

    question_count = conn.execute("""
        SELECT COUNT(*)
        FROM questions
        WHERE quiz_id = ?
    """, (quiz_id,)).fetchone()[0]

    if question_count == 0:
        conn.close()
        return False, "Add at least one question before publishing."

    conn.execute("""
        UPDATE quizzes
        SET status = 'Published'
        WHERE id = ?
          AND teacher_id = ?
          AND status = 'Draft'
    """, (quiz_id, teacher_id))

    conn.commit()
    conn.close()

    return True, "Quiz published successfully!"

def get_active_subjects():
    conn = get_connection()

    subjects = conn.execute("""
        SELECT id, name
        FROM subjects
        WHERE is_active = 1
        ORDER BY name
    """).fetchall()

    conn.close()
    return [dict(subject) for subject in subjects]


def submit_subject_request(teacher_id, subject_id, request_type):
    conn = get_connection()

    # Check that the subject is active
    subject = conn.execute("""
        SELECT id
        FROM subjects
        WHERE id = ? AND is_active = 1
    """, (subject_id,)).fetchone()

    if not subject:
        conn.close()
        return False, "This subject is unavailable."

    # Check current assignment
    assigned = conn.execute("""
        SELECT 1
        FROM teacher_subjects
        WHERE teacher_id = ? AND subject_id = ?
    """, (teacher_id, subject_id)).fetchone()

    if request_type == "ADD" and assigned:
        conn.close()
        return False, "You are already assigned to this subject."

    if request_type == "DROP" and not assigned:
        conn.close()
        return False, "You are not assigned to this subject."

    # Prevent duplicate or conflicting pending requests
    pending = conn.execute("""
        SELECT id
        FROM subject_requests
        WHERE teacher_id = ?
          AND subject_id = ?
          AND status = 'Pending'
    """, (teacher_id, subject_id)).fetchone()

    if pending:
        conn.close()
        return False, "You already have a pending request for this subject."

    # Submit the request
    conn.execute("""
        INSERT INTO subject_requests (
            teacher_id,
            subject_id,
            request_type,
            status
        )
        VALUES (?, ?, ?, 'Pending')
    """, (teacher_id, subject_id, request_type))

    conn.commit()
    conn.close()

    return True, "Your request has been submitted to the administrator."


def show_subject_request_panel(teacher_id):
    st.subheader("📚 Subject Requests")
    st.caption(
        "Request a new subject or request to drop an existing assignment. "
        "Changes take effect only after administrator approval."
    )

    assigned_subjects = get_teacher_subjects(teacher_id)
    active_subjects = get_active_subjects()

    request_type = st.radio(
        "Choose your request",
        ["Add a Subject", "Drop a Subject"],
        horizontal=True,
        key="teacher_subject_request_type"
    )

    assigned_ids = {
        subject["id"] for subject in assigned_subjects
    }

    if request_type == "Add a Subject":
        choices = active_subjects
        database_request_type = "ADD"

    else:
        choices = assigned_subjects
        database_request_type = "DROP"

    if not choices:
        if request_type == "Add a Subject":
            st.info("You are already assigned to all active subjects.")
        else:
            st.info("You have no assigned subjects to drop.")
    else:
        with st.form("teacher_subject_request_form"):
            selected_subject = st.selectbox(
                "Select Subject",
                choices,
                format_func=lambda subject: (
                    f"{subject['name']} (Already assigned)"
                    if request_type == "Add a Subject"
                    and subject["id"] in assigned_ids
                    else subject["name"]
                )
            )

            submitted = st.form_submit_button(
                "Submit Request",
                use_container_width=True
            )

            if submitted:
                success, message = submit_subject_request(
                    teacher_id,
                    selected_subject["id"],
                    database_request_type
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)

    st.divider()
    st.markdown("#### My Request History")

    conn = get_connection()

    requests = conn.execute("""
        SELECT
            s.name AS subject,
            r.request_type,
            r.status,
            r.admin_remark,
            r.requested_at,
            r.reviewed_at
        FROM subject_requests r
        JOIN subjects s ON s.id = r.subject_id
        WHERE r.teacher_id = ?
        ORDER BY r.id DESC
    """, (teacher_id,)).fetchall()

    conn.close()

    if requests:
        st.dataframe(
            [
                {
                    "Subject": request["subject"],
                    "Request": request["request_type"],
                    "Status": request["status"],
                    "Administrator Remark": request["admin_remark"] or "—",
                    "Requested At": request["requested_at"],
                    "Reviewed At": request["reviewed_at"] or "—"
                }
                for request in requests
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("You haven't submitted any subject requests yet.")

def upload_lecture(teacher_id, subject_id, title, uploaded_file):
    upload_folder = Path("uploads")
    upload_folder.mkdir(parents=True, exist_ok=True)

    safe_name = Path(uploaded_file.name).name
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    file_path = upload_folder / unique_name

    file_path.write_bytes(uploaded_file.getbuffer())

    conn = get_connection()

    conn.execute("""
        INSERT INTO learning_resources (
            subject_id,
            teacher_id,
            title,
            file_path
        )
        VALUES (?, ?, ?, ?)
    """, (
        subject_id,
        teacher_id,
        title.strip(),
        str(file_path)
    ))

    conn.commit()
    conn.close()

def get_pending_requiz_requests(teacher_id):
    conn = get_connection()

    requests = conn.execute("""
        SELECT
            r.id,
            r.student_id,
            r.quiz_id,
            r.reason,
            r.requested_at,
            u.full_name AS student_name,
            q.title AS quiz_title,
            s.name AS subject_name,
            (
                SELECT COUNT(*)
                FROM requiz_requests rr
                WHERE rr.student_id = r.student_id
                  AND rr.quiz_id = r.quiz_id
            ) AS request_count
        FROM requiz_requests r
        JOIN users u ON u.id = r.student_id
        JOIN quizzes q ON q.id = r.quiz_id
        JOIN subjects s ON s.id = q.subject_id
        WHERE q.teacher_id = ?
          AND r.status = 'Pending'
        ORDER BY r.requested_at
    """, (teacher_id,)).fetchall()

    conn.close()

    return [dict(request) for request in requests]

def review_requiz_request(request_id, status, remark):
    conn = get_connection()

    conn.execute("""
        UPDATE requiz_requests
        SET status = ?,
            teacher_remark = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND status = 'Pending'
    """, (status, remark.strip(), request_id))

    conn.commit()
    conn.close()

def get_student_report_rows(subject_id):
    conn = get_connection()

    students = conn.execute("""
        SELECT
            u.id AS student_id,
            u.full_name,
            u.username,
            u.class_name,
            COUNT(DISTINCT CASE
                WHEN a.status = 'Submitted' THEN a.id
            END) AS completed_attempts,
            ROUND(
                AVG(
                    CASE
                        WHEN a.status = 'Submitted'
                             AND a.max_score > 0
                        THEN 100.0 * a.score / a.max_score
                    END
                ),
                1
            ) AS average_score
        FROM student_subjects ss
        JOIN users u ON u.id = ss.student_id
        LEFT JOIN quizzes q
            ON q.subject_id = ss.subject_id
           AND q.status = 'Published'
        LEFT JOIN quiz_attempts a
            ON a.quiz_id = q.id
           AND a.student_id = u.id
        WHERE ss.subject_id = ?
          AND u.role = 'Student'
        GROUP BY u.id, u.full_name, u.username, u.class_name
        ORDER BY u.full_name
    """, (subject_id,)).fetchall()

    conn.close()

    return [dict(student) for student in students]


def get_student_quiz_report(student_id, subject_id):
    conn = get_connection()

    quizzes = conn.execute("""
        SELECT
            q.id AS quiz_id,
            q.title,
            a.score,
            a.max_score,
            a.status AS attempt_status,
            a.submitted_at
        FROM quizzes q
        LEFT JOIN quiz_attempts a
            ON a.id = (
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


def get_student_topic_report(student_id, subject_id):
    conn = get_connection()

    topics = conn.execute("""
        SELECT
            t.id,
            t.name,
            COUNT(aa.id) AS questions_answered,
            COALESCE(SUM(aa.is_correct), 0) AS correct_answers,
            COALESCE(SUM(aa.help_used), 0) AS help_used
        FROM topics t
        JOIN questions qu ON qu.topic_id = t.id
        JOIN quizzes q ON q.id = qu.quiz_id
        JOIN quiz_attempts a ON a.quiz_id = q.id
        JOIN attempt_answers aa
            ON aa.attempt_id = a.id
           AND aa.question_id = qu.id
        WHERE a.student_id = ?
          AND q.subject_id = ?
          AND a.status = 'Submitted'
        GROUP BY t.id, t.name
        ORDER BY t.name
    """, (student_id, subject_id)).fetchall()

    conn.close()

    results = []

    for row in topics:
        topic = dict(row)
        total = topic["questions_answered"]
        correct = topic["correct_answers"]

        accuracy = (correct / total * 100) if total else 0

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


def get_student_ai_help_count(student_id, subject_id):
    conn = get_connection()

    result = conn.execute("""
        SELECT COUNT(*) AS help_count
        FROM ai_help_logs l
        JOIN quizzes q ON q.id = l.quiz_id
        WHERE l.student_id = ?
          AND q.subject_id = ?
    """, (student_id, subject_id)).fetchone()

    conn.close()

    return result["help_count"]


def show_student_reports(subject_id, subject_name):
    st.subheader(f"📊 Student Reports — {subject_name}")

    students = get_student_report_rows(subject_id)

    if not students:
        st.info(
            "No students are enrolled in this subject yet."
        )
        return

    st.caption(
        "Select a student to inspect their quiz results, "
        "topic accuracy, and AI-help requests."
    )

    labels = {
        student["student_id"]: (
            f"{student['full_name']} "
            f"(@{student['username']})"
        )
        for student in students
    }

    selected_student_id = st.selectbox(
        "Select Student",
        list(labels.keys()),
        format_func=lambda sid: labels[sid],
        key=f"report_student_{subject_id}"
    )

    student = next(
        s for s in students
        if s["student_id"] == selected_student_id
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Quizzes Submitted",
            student["completed_attempts"]
        )

    with col2:
        average = student["average_score"]

        st.metric(
            "Average Score",
            f"{average:.1f}%"
            if average is not None
            else "—"
        )

    with col3:
        help_count = get_student_ai_help_count(
            selected_student_id,
            subject_id
        )

        st.metric("AI-Help Requests", help_count)

    st.divider()

    # Quiz results
    st.markdown("### Individual Quiz Performance")

    quiz_results = get_student_quiz_report(
        selected_student_id,
        subject_id
    )

    if not quiz_results:
        st.info("No published quizzes are available.")
    else:
        rows = []

        for quiz in quiz_results:
            status = quiz["attempt_status"]

            if status == "Submitted":
                if quiz["max_score"]:
                    score = (
                        f"{quiz['score']}/{quiz['max_score']} "
                        f"({quiz['score'] / quiz['max_score'] * 100:.1f}%)"
                    )
                else:
                    score = "Submitted"

                result_status = "Submitted"

            elif status == "In Progress":
                score = "—"
                result_status = "In Progress"

            else:
                score = "—"
                result_status = "Not Attempted"

            rows.append({
                "Quiz": quiz["title"],
                "Score": score,
                "Status": result_status,
                "Submitted At": quiz["submitted_at"] or "—"
            })

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # Topic analysis
    st.markdown("### Topic-wise Performance")

    topics = get_student_topic_report(
        selected_student_id,
        subject_id
    )

    if not topics:
        st.info(
            "Topic performance will appear after the student "
            "submits a quiz with recorded answers."
        )
    else:
        for topic in topics:
            with st.expander(
                f"{topic['name']} — {topic['level']}"
            ):
                st.write(
                    f"**Accuracy:** {topic['accuracy']}%"
                )

                st.progress(
                    topic["accuracy"] / 100
                )

                st.write(
                    f"Questions answered: "
                    f"{topic['questions_answered']}"
                )

                st.write(
                    f"Correct answers: {topic['correct_answers']}"
                )

                st.write(
                    f"AI-help usage recorded: {topic['help_used']}"
                )

                if (
                    topic["level"] == "Weak"
                    and topic["questions_answered"] >= 3
                ):
                    st.warning(
                        "Repeated difficulty detected: "
                        "review this topic with the student."
                    )
def show_teacher_dashboard(user):
    teacher_id = user["id"]

    st.title("👩‍🏫 Teacher Dashboard")
    st.caption("Create assessments, manage learning materials, and monitor students.")

    # Subject Requests
    show_subject_request_panel(teacher_id)

    st.divider()

    # Assigned Subjects
    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning("You have no approved subject assignments yet.")
        st.info(
            "Submit a subject request above. "
            "Once the administrator approves it, "
            "your assigned subjects will appear here."
        )
        return

    subject_ids = [subject["id"] for subject in subjects]

    selected_subject_id = st.selectbox(
        "Select Subject",
        subject_ids,
        format_func=lambda sid: next(
            subject["name"]
            for subject in subjects
            if subject["id"] == sid
        ),
        key="teacher_subject_select"
    )

    selected_subject = next(
        subject
        for subject in subjects
        if subject["id"] == selected_subject_id
    )

    subject_name = selected_subject["name"]

    quizzes = get_teacher_quizzes(
        teacher_id,
        selected_subject_id
    )

    total_quizzes = len(quizzes)
    published_quizzes = sum(
        quiz["status"] == "Published"
        for quiz in quizzes
    )

    conn = get_connection()

    student_count = conn.execute("""
        SELECT COUNT(DISTINCT a.student_id)
        FROM quiz_attempts a
        JOIN quizzes q ON q.id = a.quiz_id
        WHERE q.teacher_id = ?
          AND q.subject_id = ?
    """, (teacher_id, selected_subject_id)).fetchone()[0]

    conn.close()

    col1, col2, col3 = st.columns(3)

    col1.metric("Quizzes Created", total_quizzes)
    col2.metric("Published Quizzes", published_quizzes)
    col3.metric("Students Attempted", student_count)

    st.divider()

    overview_tab, create_tab, manage_tab, reports_tab, upload_tab, requiz_tab = st.tabs([
        "Overview",
        "Create Quiz",
        "Manage Quizzes",
        "Student Reports",
        "Upload Lecture",
        "Re-quiz Requests"
    ])

    # Overview
    with overview_tab:
        st.subheader(subject_name)

        if quizzes:
            quiz_df = pd.DataFrame(quizzes)

            quiz_df = quiz_df.rename(columns={
                "title": "Quiz",
                "status": "Status",
                "scheduled_at": "Scheduled At",
                "due_at": "Due At",
                "question_count": "Questions"
            })

            st.dataframe(
                quiz_df[
                    ["Quiz", "Status", "Scheduled At", "Due At", "Questions"]
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No quizzes have been created for this subject yet.")

    # Create quiz
    with create_tab:
        st.subheader("Create a Quiz")

        with st.form("create_quiz_form"):
            title = st.text_input("Quiz Title")

            description = st.text_area(
                "Description",
                placeholder="Enter the quiz instructions."
            )

            col1, col2 = st.columns(2)

            with col1:
                scheduled_date = st.date_input(
                    "Quiz Date",
                    value=date.today()
                )

                scheduled_time = st.time_input(
                    "Start Time",
                    value=(datetime.now() + timedelta(minutes=5)).time().replace(
                        second=0,
                        microsecond=0
                    )
                )

            with col2:
                due_date = st.date_input(
                    "Due Date",
                    value=date.today() + timedelta(days=1)
                )

                due_time = st.time_input(
                    "Due Time",
                    value=time(23, 59)
                )

            create_submitted = st.form_submit_button(
                "Create Draft Quiz",
                use_container_width=True
            )

            if create_submitted:
                start_datetime = datetime.combine(
                    scheduled_date,
                    scheduled_time
                )

                due_datetime = datetime.combine(
                    due_date,
                    due_time
                )

                if not title.strip():
                    st.error("Please enter a quiz title.")

                elif due_datetime <= start_datetime:
                    st.error("The due date and time must be after the start time.")

                else:
                    new_quiz_id = create_quiz(
                        teacher_id,
                        selected_subject_id,
                        title,
                        description,
                        start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                        due_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    )

                    st.session_state["teacher_active_quiz_id"] = new_quiz_id

                    st.success("Draft created! You can now add questions.")
                    st.rerun()

        st.divider()

        st.subheader("Add Topics")

        with st.form("add_topic_form"):
            new_topic_name = st.text_input(
                "Topic Name",
                placeholder="Example: Binary Trees"
            )

            topic_submitted = st.form_submit_button("Add Topic")

            if topic_submitted:
                if not new_topic_name.strip():
                    st.error("Enter a topic name.")
                elif create_topic(selected_subject_id, new_topic_name):
                    st.success("Topic added successfully!")
                    st.rerun()
                else:
                    st.error("This topic may already exist.")

        topics = get_subject_topics(selected_subject_id)

        if topics:
            st.caption(
                "Available topics: "
                + ", ".join(topic["name"] for topic in topics)
            )
        else:
            st.warning("Add at least one topic before creating questions.")

        st.divider()

        st.subheader("Add Questions to a Draft")

        drafts = [
            quiz for quiz in quizzes
            if quiz["status"] == "Draft"
        ]

        if not drafts:
            st.info("Create a draft quiz first.")
        elif not topics:
            st.warning("Add a topic before adding questions.")
        else:
            draft_ids = [quiz["id"] for quiz in drafts]

            default_id = st.session_state.get("teacher_active_quiz_id")

            selected_draft_id = st.selectbox(
                "Select Draft Quiz",
                draft_ids,
                index=(
                    draft_ids.index(default_id)
                    if default_id in draft_ids
                    else 0
                ),
                format_func=lambda qid: next(
                    quiz["title"]
                    for quiz in drafts
                    if quiz["id"] == qid
                ),
                key="teacher_draft_select"
            )

            with st.form(f"add_question_form_{selected_draft_id}"):
                topic_ids = [topic["id"] for topic in topics]

                topic_id = st.selectbox(
                    "Question Topic",
                    topic_ids,
                    format_func=lambda tid: next(
                        topic["name"]
                        for topic in topics
                        if topic["id"] == tid
                    )
                )

                question_text = st.text_area("Question")

                option_a = st.text_input("Option A")
                option_b = st.text_input("Option B")
                option_c = st.text_input("Option C")
                option_d = st.text_input("Option D")

                correct_answer = st.selectbox(
                    "Correct Answer",
                    ["A", "B", "C", "D"]
                )

                explanation = st.text_area(
                    "Explanation",
                    placeholder="Explain why the answer is correct."
                )

                col1, col2 = st.columns(2)

                with col1:
                    difficulty = st.selectbox(
                        "Difficulty",
                        ["Easy", "Medium", "Hard"]
                    )

                with col2:
                    marks = st.number_input(
                        "Marks",
                        min_value=1,
                        max_value=100,
                        value=1
                    )

                question_submitted = st.form_submit_button(
                    "Add Question",
                    use_container_width=True
                )

                if question_submitted:
                    if not all([
                        question_text.strip(),
                        option_a.strip(),
                        option_b.strip(),
                        option_c.strip(),
                        option_d.strip()
                    ]):
                        st.error("Fill in the question and all four options.")
                    else:
                        add_question(
                            selected_draft_id,
                            topic_id,
                            question_text,
                            option_a,
                            option_b,
                            option_c,
                            option_d,
                            correct_answer,
                            explanation,
                            difficulty,
                            marks
                        )

                        st.success("Question added successfully!")
                        st.rerun()

            existing_questions = get_quiz_questions(selected_draft_id)

            st.markdown("#### Questions Added")

            if existing_questions:
                for number, question in enumerate(existing_questions, start=1):
                    with st.expander(
                        f"Question {number}: {question['question_text']}"
                    ):
                        st.write(f"**Topic:** {question['topic']}")
                        st.write(f"**Difficulty:** {question['difficulty']}")
                        st.write(f"**Marks:** {question['marks']}")
                        st.write(
                            f"**Correct Answer:** {question['correct_answer']}"
                        )
            else:
                st.info("No questions added yet.")

            st.divider()

            if st.button(
                "Publish Quiz",
                key=f"publish_quiz_{selected_draft_id}",
                use_container_width=True
            ):
                success, message = publish_quiz(
                    selected_draft_id,
                    teacher_id
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

            st.caption(
                "Only publish when your questions and correct answers "
                "have been checked."
            )

    # Manage quizzes
    with manage_tab:
        st.subheader(f"Manage {subject_name} Quizzes")

        if not quizzes:
            st.info("No quizzes to manage.")
        else:
            for quiz in quizzes:
                with st.expander(
                    f"{quiz['title']} — {quiz['status']}"
                ):
                    st.write(f"**Scheduled:** {quiz['scheduled_at']}")
                    st.write(f"**Due:** {quiz['due_at']}")
                    st.write(f"**Questions:** {quiz['question_count']}")

                    if quiz["status"] == "Published":
                        questions = get_quiz_questions(quiz["id"])

                        for number, question in enumerate(
                            questions,
                            start=1
                        ):
                            st.write(
                                f"{number}. {question['question_text']}"
                            )

                            st.caption(
                                f"Topic: {question['topic']} | "
                                f"Answer: {question['correct_answer']}"
                            )

    # Student Reports
    with reports_tab:
        show_student_reports(
            selected_subject_id,
            subject_name
        )

    # Upload lecture
    with upload_tab:
        st.subheader("Upload Lecture Material")

        with st.form("lecture_upload_form"):
            lecture_title = st.text_input("Lecture Title")

            uploaded_file = st.file_uploader(
                "Choose a lecture file",
                type=["pdf", "ppt", "pptx", "doc", "docx", "txt"]
            )

            upload_submitted = st.form_submit_button("Upload Lecture")

            if upload_submitted:
                if not lecture_title.strip():
                    st.error("Enter a lecture title.")
                elif uploaded_file is None:
                    st.error("Select a file to upload.")
                else:
                    try:
                        upload_lecture(
                            teacher_id,
                            selected_subject_id,
                            lecture_title,
                            uploaded_file
                        )

                        st.success("Lecture uploaded successfully!")

                    except Exception as error:
                        st.error(f"Upload failed: {error}")

        st.caption("Uploaded files are stored in the project's uploads folder.")

    # Re-quiz requests
    with requiz_tab:
        st.subheader("Student Re-quiz Requests")

        requests = get_pending_requiz_requests(teacher_id)

        if not requests:
            st.info("No pending re-quiz requests.")
        else:
            for request in requests:
                with st.expander(
                    f"{request['student_name']} — {request['quiz_title']}"
                ):
                    st.write(f"**Subject:** {request['subject_name']}")
                    st.write(f"**Total re-quiz requests:** {request['request_count']}")
                    st.write(f"**Reason:** {request['reason'] or 'Not provided'}")

                    remark = st.text_area(
                        "Teacher Remark",
                        key=f"requiz_remark_{request['id']}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "Approve",
                            key=f"approve_{request['id']}",
                            use_container_width=True
                        ):
                            review_requiz_request(
                                request["id"],
                                "Approved",
                                remark
                            )

                            st.success("Request approved.")
                            st.rerun()

                    with col2:
                        if st.button(
                            "Reject",
                            key=f"reject_{request['id']}",
                            use_container_width=True
                        ):
                            if not remark.strip():
                                st.warning(
                                    "Enter a remark before rejecting."
                                )
                            else:
                                review_requiz_request(
                                    request["id"],
                                    "Rejected",
                                    remark
                                )

                                st.success("Request rejected.")
                                st.rerun()