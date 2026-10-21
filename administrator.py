import streamlit as st
import pandas as pd

from database import get_connection


def get_teachers():
    conn = get_connection()

    teachers = conn.execute("""
        SELECT id, username, full_name
        FROM users
        WHERE role = 'Teacher'
        ORDER BY full_name
    """).fetchall()

    conn.close()
    return [dict(row) for row in teachers]


def get_subjects(active_only=False):
    conn = get_connection()

    query = "SELECT id, name, is_active FROM subjects"

    if active_only:
        query += " WHERE is_active = 1"

    query += " ORDER BY name"

    subjects = conn.execute(query).fetchall()
    conn.close()

    return [dict(row) for row in subjects]


def get_teacher_assignments():
    conn = get_connection()

    assignments = conn.execute("""
        SELECT
            ts.teacher_id,
            ts.subject_id,
            u.full_name AS teacher_name,
            u.username,
            s.name AS subject_name
        FROM teacher_subjects ts
        JOIN users u ON u.id = ts.teacher_id
        JOIN subjects s ON s.id = ts.subject_id
        ORDER BY u.full_name, s.name
    """).fetchall()

    conn.close()
    return [dict(row) for row in assignments]


def show_administrator_dashboard(user=None):
    st.title("Administrator Dashboard")
    st.caption("Manage subjects, teachers, and subject assignments.")

    tab1, tab2, tab3 = st.tabs([
        "Manage Subjects",
        "Teacher Assignments",
        "Subject Requests"
    ])

    # Manage subjects
    with tab1:
        st.subheader("Add a Subject")

        with st.form("add_subject_form"):
            subject_name = st.text_input(
                "Subject Name",
                placeholder="Example: Artificial Intelligence"
            )

            add_submitted = st.form_submit_button("Add Subject")

            if add_submitted:
                if not subject_name.strip():
                    st.error("Enter a subject name.")
                else:
                    conn = get_connection()

                    existing = conn.execute("""
                        SELECT id, is_active
                        FROM subjects
                        WHERE name = ?
                    """, (subject_name.strip(),)).fetchone()

                    if existing:
                        if existing["is_active"]:
                            st.warning("This subject already exists.")
                        else:
                            conn.execute("""
                                UPDATE subjects
                                SET is_active = 1
                                WHERE id = ?
                            """, (existing["id"],))

                            conn.commit()
                            st.success("Subject reactivated.")
                            st.rerun()
                    else:
                        conn.execute("""
                            INSERT INTO subjects (name)
                            VALUES (?)
                        """, (subject_name.strip(),))

                        conn.commit()
                        st.success("Subject added successfully!")
                        st.rerun()

                    conn.close()

        st.divider()
        st.subheader("Available Subjects")

        subjects = get_subjects()

        if subjects:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Subject": s["name"],
                        "Status": (
                            "Active" if s["is_active"] else "Inactive"
                        )
                    }
                    for s in subjects
                ]),
                use_container_width=True,
                hide_index=True
            )

            active_subjects = [
                s for s in subjects if s["is_active"]
            ]

            if active_subjects:
                selected_subject = st.selectbox(
                    "Select a subject to deactivate",
                    [s["id"] for s in active_subjects],
                    format_func=lambda sid: next(
                        s["name"] for s in active_subjects
                        if s["id"] == sid
                    ),
                    key="deactivate_subject"
                )

                if st.button("Deactivate Subject"):
                    conn = get_connection()

                    conn.execute("""
                        UPDATE subjects
                        SET is_active = 0
                        WHERE id = ?
                    """, (selected_subject,))

                    conn.commit()
                    conn.close()

                    st.success(
                        "Subject deactivated. Historical records are preserved."
                    )
                    st.rerun()
        else:
            st.info("No subjects have been added yet.")

    # Teacher assignments
    with tab2:
        st.subheader("Assign Subjects to Teachers")

        teachers = get_teachers()
        active_subjects = get_subjects(active_only=True)

        if not teachers:
            st.warning("No teacher accounts are registered.")
        elif not active_subjects:
            st.warning("Add an active subject before assigning it.")
        else:
            with st.form("assign_subject_form"):
                teacher_id = st.selectbox(
                    "Select Teacher",
                    [t["id"] for t in teachers],
                    format_func=lambda tid: next(
                        f"{t['full_name']} (@{t['username']})"
                        for t in teachers if t["id"] == tid
                    )
                )

                subject_id = st.selectbox(
                    "Select Subject",
                    [s["id"] for s in active_subjects],
                    format_func=lambda sid: next(
                        s["name"] for s in active_subjects
                        if s["id"] == sid
                    )
                )

                assign_submitted = st.form_submit_button(
                    "Approve and Assign Subject"
                )

                if assign_submitted:
                    conn = get_connection()

                    conn.execute("""
                        INSERT OR IGNORE INTO teacher_subjects
                        (teacher_id, subject_id)
                        VALUES (?, ?)
                    """, (teacher_id, subject_id))

                    conn.commit()
                    conn.close()

                    st.success(
                        "Subject assigned to the teacher successfully."
                    )
                    st.rerun()

        st.divider()
        st.subheader("Current Teacher Assignments")

        assignments = get_teacher_assignments()

        if assignments:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Teacher": a["teacher_name"],
                        "Username": a["username"],
                        "Subject": a["subject_name"]
                    }
                    for a in assignments
                ]),
                use_container_width=True,
                hide_index=True
            )

            selected_assignment = st.selectbox(
                "Select an assignment to remove",
                range(len(assignments)),
                format_func=lambda i: (
                    f"{assignments[i]['teacher_name']} — "
                    f"{assignments[i]['subject_name']}"
                ),
                key="remove_assignment"
            )

            if st.button("Remove Teacher Assignment"):
                assignment = assignments[selected_assignment]

                conn = get_connection()

                conn.execute("""
                    DELETE FROM teacher_subjects
                    WHERE teacher_id = ?
                      AND subject_id = ?
                """, (
                    assignment["teacher_id"],
                    assignment["subject_id"]
                ))

                conn.commit()
                conn.close()

                st.success("Teacher assignment removed.")
                st.rerun()
        else:
            st.info("No teacher assignments exist yet.")

    # Subject requests
    with tab3:
        st.subheader("Pending Teacher Requests")

        conn = get_connection()

        requests = conn.execute("""
            SELECT
                r.id,
                r.teacher_id,
                r.subject_id,
                r.request_type,
                r.requested_at,
                u.full_name AS teacher_name,
                u.username,
                s.name AS subject_name
            FROM subject_requests r
            JOIN users u ON u.id = r.teacher_id
            JOIN subjects s ON s.id = r.subject_id
            WHERE r.status = 'Pending'
            ORDER BY r.requested_at
        """).fetchall()

        conn.close()

        requests = [dict(row) for row in requests]

        if not requests:
            st.info("There are no pending subject requests.")
        else:
            for request in requests:
                with st.expander(
                    f"{request['teacher_name']} — "
                    f"{request['request_type']} — "
                    f"{request['subject_name']}"
                ):
                    st.write(
                        f"**Teacher username:** {request['username']}"
                    )
                    st.write(
                        f"**Request:** {request['request_type']} "
                        f"{request['subject_name']}"
                    )

                    remark = st.text_input(
                        "Administrator Remark",
                        key=f"remark_{request['id']}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "Approve",
                            key=f"approve_{request['id']}"
                        ):
                            conn = get_connection()

                            subject = conn.execute("""
                                SELECT is_active
                                FROM subjects
                                WHERE id = ?
                            """, (request["subject_id"],)).fetchone()

                            if not subject or not subject["is_active"]:
                                st.error(
                                    "This subject is inactive. "
                                    "Reactivate it before approving."
                                )
                                conn.close()
                            else:
                                if request["request_type"] == "ADD":
                                    conn.execute("""
                                        INSERT OR IGNORE INTO teacher_subjects
                                        (teacher_id, subject_id)
                                        VALUES (?, ?)
                                    """, (
                                        request["teacher_id"],
                                        request["subject_id"]
                                    ))

                                elif request["request_type"] == "DROP":
                                    conn.execute("""
                                        DELETE FROM teacher_subjects
                                        WHERE teacher_id = ?
                                          AND subject_id = ?
                                    """, (
                                        request["teacher_id"],
                                        request["subject_id"]
                                    ))

                                conn.execute("""
                                    UPDATE subject_requests
                                    SET status = 'Approved',
                                        admin_remark = ?,
                                        reviewed_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                      AND status = 'Pending'
                                """, (remark.strip(), request["id"]))

                                conn.commit()
                                conn.close()

                                st.success("Request approved.")
                                st.rerun()

                    with col2:
                        if st.button(
                            "Reject",
                            key=f"reject_{request['id']}"
                        ):
                            if not remark.strip():
                                st.warning(
                                    "Enter a remark before rejecting."
                                )
                            else:
                                conn = get_connection()

                                conn.execute("""
                                    UPDATE subject_requests
                                    SET status = 'Rejected',
                                        admin_remark = ?,
                                        reviewed_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                      AND status = 'Pending'
                                """, (remark.strip(), request["id"]))

                                conn.commit()
                                conn.close()

                                st.success("Request rejected.")
                                st.rerun()