import streamlit as st
from datetime import datetime

from database import get_connection


def get_published_quizzes(student_id):
    conn = get_connection()

    quizzes = conn.execute("""
        SELECT
            q.id,
            q.title,
            q.description,
            q.scheduled_at,
            q.due_at,
            s.name AS subject_name
        FROM quizzes q
        JOIN subjects s ON s.id = q.subject_id
        JOIN student_subjects ss ON ss.subject_id = q.subject_id
        WHERE ss.student_id = ?
          AND q.status = 'Published'
          AND s.is_active = 1
        ORDER BY q.scheduled_at
    """, (student_id,)).fetchall()

    conn.close()

    return [dict(quiz) for quiz in quizzes]


def get_attempt(student_id, quiz_id):
    conn = get_connection()

    attempt = conn.execute("""
        SELECT *
        FROM quiz_attempts
        WHERE student_id = ? AND quiz_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (student_id, quiz_id)).fetchone()

    conn.close()

    return dict(attempt) if attempt else None


def get_questions(quiz_id):
    conn = get_connection()

    questions = conn.execute("""
        SELECT
            id,
            quiz_id,
            topic_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
            marks
        FROM questions
        WHERE quiz_id = ?
        ORDER BY id
    """, (quiz_id,)).fetchall()

    conn.close()

    return [dict(question) for question in questions]


def quiz_availability(quiz):
    now = datetime.now()

    start = (
        datetime.fromisoformat(quiz["scheduled_at"])
        if quiz["scheduled_at"]
        else None
    )

    due = (
        datetime.fromisoformat(quiz["due_at"])
        if quiz["due_at"]
        else None
    )

    if start and now < start:
        return "Upcoming"

    if due and now > due:
        return "Closed"

    return "Available"


def start_attempt(student_id, quiz_id):
    conn = get_connection()

    existing = conn.execute("""
        SELECT id
        FROM quiz_attempts
        WHERE student_id = ?
          AND quiz_id = ?
          AND status = 'In Progress'
        ORDER BY id DESC
        LIMIT 1
    """, (student_id, quiz_id)).fetchone()

    if existing:
        attempt_id = existing["id"]
    else:
        max_score = conn.execute("""
            SELECT COALESCE(SUM(marks), 0)
            FROM questions
            WHERE quiz_id = ?
        """, (quiz_id,)).fetchone()[0]

        cursor = conn.execute("""
            INSERT INTO quiz_attempts (
                student_id,
                quiz_id,
                score,
                max_score,
                status,
                started_at
            )
            VALUES (?, ?, 0, ?, 'In Progress', ?)
        """, (
            student_id,
            quiz_id,
            max_score,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        attempt_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return attempt_id


def record_ai_help(student_id, attempt_id, quiz_id, question):
    conn = get_connection()

    conn.execute("""
        INSERT INTO ai_help_logs (
            student_id,
            quiz_id,
            question_id,
            topic_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        student_id,
        quiz_id,
        question["id"],
        question["topic_id"]
    ))

    selected = st.session_state.get(
        f"answer_{attempt_id}_{question['id']}"
    )

    existing = conn.execute("""
        SELECT help_used
        FROM attempt_answers
        WHERE attempt_id = ? AND question_id = ?
    """, (attempt_id, question["id"])).fetchone()

    help_used = 1 if existing and existing["help_used"] else 0

    conn.execute("""
        INSERT INTO attempt_answers (
            attempt_id,
            question_id,
            selected_answer,
            is_correct,
            help_used
        )
        VALUES (?, ?, ?, 0, 1)
        ON CONFLICT(attempt_id, question_id)
        DO UPDATE SET
            selected_answer = excluded.selected_answer,
            help_used = 1
    """, (
        attempt_id,
        question["id"],
        selected
    ))

    conn.commit()
    conn.close()


def submit_attempt(student_id, quiz_id, attempt_id, questions):
    conn = get_connection()

    attempt = conn.execute("""
        SELECT id, status
        FROM quiz_attempts
        WHERE id = ?
          AND student_id = ?
          AND quiz_id = ?
    """, (attempt_id, student_id, quiz_id)).fetchone()

    if not attempt or attempt["status"] != "In Progress":
        conn.close()
        return None

    due = conn.execute("""
        SELECT due_at
        FROM quizzes
        WHERE id = ?
    """, (quiz_id,)).fetchone()

    if due and due["due_at"]:
        due_time = datetime.fromisoformat(due["due_at"])

        if datetime.now() > due_time:
            conn.close()
            return None

    score = 0
    max_score = sum(question["marks"] for question in questions)

    for question in questions:
        question_id = question["id"]

        selected = st.session_state.get(
            f"answer_{attempt_id}_{question_id}"
        )

        correct = int(
            selected is not None
            and selected == question["correct_answer"]
        )

        if correct:
            score += question["marks"]

        existing = conn.execute("""
            SELECT help_used
            FROM attempt_answers
            WHERE attempt_id = ? AND question_id = ?
        """, (attempt_id, question_id)).fetchone()

        help_used = (
            1 if existing and existing["help_used"] else 0
        )

        conn.execute("""
            INSERT INTO attempt_answers (
                attempt_id,
                question_id,
                selected_answer,
                is_correct,
                help_used
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET
                selected_answer = excluded.selected_answer,
                is_correct = excluded.is_correct,
                help_used = MAX(
                    attempt_answers.help_used,
                    excluded.help_used
                )
        """, (
            attempt_id,
            question_id,
            selected,
            correct,
            help_used
        ))

    conn.execute("""
        UPDATE quiz_attempts
        SET score = ?,
            max_score = ?,
            status = 'Submitted',
            submitted_at = ?
        WHERE id = ?
          AND status = 'In Progress'
    """, (
        score,
        max_score,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        attempt_id
    ))

    conn.commit()
    conn.close()

    return score, max_score

def get_approved_requiz_request(student_id, quiz_id):
    conn = get_connection()

    request = conn.execute("""
        SELECT id
        FROM requiz_requests
        WHERE student_id = ?
          AND quiz_id = ?
          AND status = 'Approved'
        ORDER BY id DESC
        LIMIT 1
    """, (student_id, quiz_id)).fetchone()

    conn.close()

    return dict(request) if request else None


def mark_requiz_used(request_id):
    conn = get_connection()

    conn.execute("""
        UPDATE requiz_requests
        SET status = 'Used'
        WHERE id = ?
          AND status = 'Approved'
    """, (request_id,))

    conn.commit()
    conn.close()


def show_attempt_review(attempt_id, questions):
    conn = get_connection()

    answers = conn.execute("""
        SELECT question_id, selected_answer, is_correct, help_used
        FROM attempt_answers
        WHERE attempt_id = ?
    """, (attempt_id,)).fetchall()

    conn.close()

    answer_map = {
        answer["question_id"]: dict(answer)
        for answer in answers
    }

    with st.expander("📝 Review Your Answers", expanded=True):
        for number, question in enumerate(questions, start=1):
            answer = answer_map.get(question["id"], {})

            selected = answer.get("selected_answer")
            correct = question["correct_answer"]

            st.markdown(
                f"**Question {number}: {question['question_text']}**"
            )

            def format_answer(letter):
                if not letter:
                    return "Not answered"

                option = question.get(
                    "option_" + letter.lower()
                )

                return f"{letter}. {option or ''}"

            st.write(
                f"**Your answer:** {format_answer(selected)}"
            )

            st.write(
                f"**Correct answer:** {format_answer(correct)}"
            )

            if selected == correct:
                st.success("Correct answer! ✅")
            else:
                st.error("Incorrect answer ❌")

            if question.get("explanation"):
                st.info(
                    f"**Explanation:** {question['explanation']}"
                )

            if answer.get("help_used"):
                st.caption("💡 You requested AI help for this question.")

            st.divider()

def show_student_quizzes(student_id):
    st.subheader("📝 Take Your Quiz")

    quizzes = get_published_quizzes(student_id)

    if not quizzes:
        st.info("No published quizzes are available for your subjects yet.")
        return

    for quiz in quizzes:
        quiz_id = quiz["id"]
        attempt = get_attempt(student_id, quiz_id)
        availability = quiz_availability(quiz)

        with st.expander(
            f"{quiz['title']} — {quiz['subject_name']}",
            expanded=bool(
                attempt and attempt["status"] == "In Progress"
            )
        ):
            st.write(f"**Subject:** {quiz['subject_name']}")

            if quiz["description"]:
                st.write(quiz["description"])

            st.write(
                f"**Starts:** {quiz['scheduled_at'] or 'Not specified'}"
            )
            st.write(
                f"**Due:** {quiz['due_at'] or 'No deadline'}"
            )

            if attempt and attempt["status"] == "Submitted":
                st.success("Quiz submitted successfully!")

                if attempt["max_score"] > 0:
                    percentage = (attempt["score"] / attempt["max_score"]) * 100

                    st.metric(
                        "Your Score",
                        f"{attempt['score']} / {attempt['max_score']}",
                        f"{percentage:.1f}%"
                    )

                # Review answers
                submitted_questions = get_questions(quiz_id)

                show_attempt_review(
                    attempt["id"],
                    submitted_questions
                )

                # Check re-quiz approval
                approved_request = get_approved_requiz_request(
                    student_id,
                    quiz_id
                )

                if approved_request:
                    st.success(
                        "Your teacher has approved your re-quiz request!"
                    )

                    if st.button(
                        "🔄 Start Approved Re-quiz",
                        key=f"start_requiz_{quiz_id}_{approved_request['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        start_attempt(student_id, quiz_id)

                        mark_requiz_used(
                            approved_request["id"]
                        )

                        st.rerun()

                else:
                    st.caption(
                        "You have completed this quiz. "
                        "Request a re-quiz from the Quiz Performance section "
                        "if you need another attempt."
                    )

                continue

            if not attempt and availability != "Available":
                if availability == "Upcoming":
                    st.info("This quiz is not open yet.")
                else:
                    st.warning("The deadline for this quiz has passed.")

                continue

            if availability == "Closed":
                st.warning("The deadline has passed. You cannot submit this quiz.")
                continue

            if attempt and attempt["status"] == "In Progress":
                attempt_id = attempt["id"]

            else:
                questions = get_questions(quiz_id)

                if not questions:
                    st.warning("This quiz has no questions yet.")
                    continue

                if st.button(
                    "Start Quiz",
                    key=f"start_{student_id}_{quiz_id}",
                    type="primary"
                ):
                    start_attempt(student_id, quiz_id)
                    st.rerun()

                st.caption("Click Start Quiz when you are ready.")
                continue

            questions = get_questions(quiz_id)

            if not questions:
                st.warning("This quiz contains no questions.")
                continue

            st.write(f"**Total Questions:** {len(questions)}")

            st.divider()

            for number, question in enumerate(questions, start=1):
                st.markdown(
                    f"**Q{number}. {question['question_text']}**"
                )

                options = ["A", "B", "C", "D"]

                selected = st.radio(
                    f"Choose your answer for Question {number}",
                    options,
                    format_func=lambda letter, q=question: (
                        f"{letter}. {q['option_' + letter.lower()]}"
                    ),
                    key=f"answer_{attempt_id}_{question['id']}",
                    index=None,
                    label_visibility="collapsed"
                )

                help_col, marks_col = st.columns([2, 1])

                with help_col:
                    if st.button(
                        "💡 Need AI Help?",
                        key=f"help_{attempt_id}_{question['id']}"
                    ):
                        record_ai_help(
                            student_id,
                            attempt_id,
                            quiz_id,
                            question
                        )

                        st.info(
                            "Your help request has been recorded. "
                            "This version tracks which questions need help; "
                            "automated AI-generated hints are not connected yet."
                        )

                with marks_col:
                    st.caption(f"Marks: {question['marks']}")

                st.divider()

            st.warning(
                "Review your answers before submitting. "
                "Submitted quizzes cannot be edited."
            )

            if st.button(
                "Submit Quiz",
                key=f"submit_{attempt_id}",
                type="primary",
                use_container_width=True
            ):
                result = submit_attempt(
                    student_id,
                    quiz_id,
                    attempt_id,
                    questions
                )

                if result is None:
                    st.error(
                        "This attempt could not be submitted. "
                        "It may already be submitted or the deadline has passed."
                    )
                else:
                    score, max_score = result

                    st.success("Quiz submitted successfully!")

                    st.metric(
                        "Final Score",
                        f"{score} / {max_score}",
                        (
                            f"{(score / max_score) * 100:.1f}%"
                            if max_score
                            else "No marks available"
                        )
                    )

                    st.rerun()