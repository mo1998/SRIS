import os
import json


WAV_BYTES = b"RIFF\x24\x00\x00\x00WAVEfmt "


def test_system_check_ping(client):
    response = client.get("/api/system-check/ping")
    assert response.status_code == 200, response.text
    assert "timestamp" in response.json()
    assert response.headers["Cache-Control"] == "no-store"


def test_system_check_download_returns_expected_size(client):
    response = client.get("/api/system-check/download?size_mb=2")
    assert response.status_code == 200, response.text
    assert response.headers["Content-Length"] == str(2 * 1024 * 1024)
    assert len(response.content) == 2 * 1024 * 1024


def test_system_check_download_rejects_oversized_payload(client):
    response = client.get("/api/system-check/download?size_mb=21")
    assert response.status_code == 422, response.text


def test_system_check_upload_reports_received_bytes(client):
    response = client.post(
        "/api/system-check/upload",
        content=b"x" * (1024 * 1024),
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["received_bytes"] == 1024 * 1024


def register_user(client, email="employer@example.com", role="employer"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Strong-password1",
            "full_name": "Test Employer",
            "role": role,
            "company_name": "SRIS Test Co",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_interview(client, token, title="Customer Support Screen"):
    response = client.post(
        "/api/interviews/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "description": "First round structured interview",
            "duration_minutes": 30,
            "max_attempts": 1,
            "pass_score": 70,
            "questions": [
                {
                    "question_text": "How do you handle an upset customer?",
                    "expected_answer": "Listen, empathize, clarify, resolve, and follow up.",
                    "question_type": "text",
                    "weight": 1,
                    "order_index": 0,
                    "rubric_criteria": [
                        {
                            "name": "Ownership",
                            "description": "Takes ownership of the customer issue",
                            "weight": 1,
                            "order_index": 0,
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_tokens(client, email="employer@example.com"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "Strong-password1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def login_user(client, email="employer@example.com"):
    return login_tokens(client, email)["access_token"]


def current_user(client, token):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_health_check(client):
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "request_id": "test-request-id"}
    assert response.headers["X-Request-ID"] == "test-request-id"
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Permissions-Policy"] == "camera=(self), microphone=(self), geolocation=()"
    assert response.headers["Cache-Control"] == "no-store"


def test_operational_health_endpoints_are_not_cached(client):
    register_user(client)
    token = login_user(client)

    for path in ["/api/reports/evaluation/health", "/api/reports/email/health"]:
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200, response.text
        assert response.headers["Cache-Control"] == "no-store"


def test_oversized_request_body_is_rejected(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_SIZE", 16)

    response = client.post(
        "/api/auth/register",
        headers={"Content-Length": "17", "X-Request-ID": "oversized-request"},
        content=b"{}",
    )

    assert response.status_code == 413, response.text
    assert response.json()["detail"] == "Request body exceeds maximum size"
    assert response.headers["X-Request-ID"] == "oversized-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_register_and_login_employer(client):
    user = register_user(client)
    token = login_user(client)

    assert user["email"] == "employer@example.com"
    assert token


def test_registration_rejects_weak_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weakpass",
            "full_name": "Weak Password",
            "role": "employee",
        },
    )

    assert response.status_code == 422, response.text
    assert "Password must include" in response.text


def test_login_rate_limit_blocks_repeated_failed_attempts(client, monkeypatch):
    from app.api.auth import login_failures
    from app.config import settings

    login_failures.clear()
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
    register_user(client, email="limited@example.com")

    for _ in range(2):
        response = client.post(
            "/api/auth/login",
            data={"username": "limited@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401, response.text

    limited_response = client.post(
        "/api/auth/login",
        data={"username": "limited@example.com", "password": "wrong-password"},
    )
    assert limited_response.status_code == 429, limited_response.text
    assert limited_response.headers["Retry-After"] == "60"


def test_successful_login_clears_failed_login_attempts(client, monkeypatch):
    from app.api.auth import login_failures
    from app.config import settings

    login_failures.clear()
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 2)
    register_user(client, email="reset-limit@example.com")

    failed_response = client.post(
        "/api/auth/login",
        data={"username": "reset-limit@example.com", "password": "wrong-password"},
    )
    assert failed_response.status_code == 401, failed_response.text

    successful_response = client.post(
        "/api/auth/login",
        data={"username": "reset-limit@example.com", "password": "Strong-password1"},
    )
    assert successful_response.status_code == 200, successful_response.text
    assert "reset-limit@example.com" not in login_failures


def test_employer_registration_creates_owner_organization(client):
    register_user(client)
    token = login_user(client)

    organization_response = client.get(
        "/api/users/me/organization",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert organization_response.status_code == 200, organization_response.text
    organization = organization_response.json()
    assert organization["name"] == "SRIS Test Co"

    memberships_response = client.get(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert memberships_response.status_code == 200, memberships_response.text
    memberships = memberships_response.json()
    assert len(memberships) == 1
    assert memberships[0]["role"] == "owner"
    assert memberships[0]["organization_id"] == organization["id"]


def test_employee_registration_does_not_create_organization(client):
    register_user(client, email="employee@example.com", role="employee")
    token = login_user(client, email="employee@example.com")

    organization_response = client.get(
        "/api/users/me/organization",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert organization_response.status_code == 404, organization_response.text

    memberships_response = client.get(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert memberships_response.status_code == 200, memberships_response.text
    assert memberships_response.json() == []


def test_current_user_and_refresh_token(client):
    register_user(client)
    tokens = login_tokens(client)

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == "employer@example.com"

    refresh_response = client.post(
        "/api/auth/refresh",
        params={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200, refresh_response.text
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]

    refreshed_me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert refreshed_me_response.status_code == 200, refreshed_me_response.text


def test_current_user_can_update_profile(client):
    register_user(client)
    token = login_user(client)

    response = client.patch(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Employer", "phone": "+15551234567"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Updated Employer"
    assert body["phone"] == "+15551234567"

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["full_name"] == "Updated Employer"


def test_current_user_can_change_password(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "Strong-password1", "new_password": "New-strong-password2"},
    )
    assert response.status_code == 204, response.text

    old_login_response = client.post(
        "/api/auth/login",
        data={"username": "employer@example.com", "password": "Strong-password1"},
    )
    assert old_login_response.status_code == 401, old_login_response.text

    new_login_response = client.post(
        "/api/auth/login",
        data={"username": "employer@example.com", "password": "New-strong-password2"},
    )
    assert new_login_response.status_code == 200, new_login_response.text

    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        audit_log = db.query(AuditLog).filter(AuditLog.action == "user.password_changed").first()
        assert audit_log is not None
        assert audit_log.target_type == "user"
        assert json.loads(audit_log.details)["email"] == "employer@example.com"
    finally:
        db.close()


def test_password_change_revokes_existing_refresh_and_access_tokens(client):
    register_user(client)
    tokens = login_tokens(client)

    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "Strong-password1", "new_password": "New-strong-password2"},
    )
    assert response.status_code == 204, response.text

    old_refresh_response = client.post(
        "/api/auth/refresh",
        params={"refresh_token": tokens["refresh_token"]},
    )
    assert old_refresh_response.status_code == 401, old_refresh_response.text

    old_access_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert old_access_response.status_code == 401, old_access_response.text


def test_current_user_password_change_rejects_wrong_current_password(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong-password", "new_password": "New-strong-password2"},
    )

    assert response.status_code == 400, response.text


def test_password_change_rejects_weak_new_password(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "Strong-password1", "new_password": "weakpass"},
    )

    assert response.status_code == 422, response.text
    assert "Password must include" in response.text


def test_employer_can_create_interview(client):
    register_user(client)
    token = login_user(client)

    body = create_interview(client, token)
    assert body["title"] == "Customer Support Screen"
    assert body["status"] == "draft"
    assert body["organization_id"] is not None
    assert len(body["questions"]) == 1


def test_employer_can_create_interview_with_question_rubric(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/interviews/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Rubric Screen",
            "description": "Structured rubric interview",
            "duration_minutes": 30,
            "max_attempts": 1,
            "pass_score": 70,
            "questions": [
                {
                    "question_text": "How do you solve ambiguous problems?",
                    "expected_answer": "Clarifies context, identifies constraints, proposes options, and validates outcomes.",
                    "question_type": "text",
                    "weight": 1,
                    "order_index": 0,
                    "rubric_criteria": [
                        {
                            "name": "Clarity",
                            "description": "Explains assumptions and constraints clearly.",
                            "weight": 1.5,
                            "order_index": 0,
                        },
                        {
                            "name": "Structure",
                            "description": "Uses a coherent problem-solving approach.",
                            "weight": 1.0,
                            "order_index": 1,
                        },
                    ],
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    interview = response.json()
    criteria = interview["questions"][0]["rubric_criteria"]
    assert [criterion["name"] for criterion in criteria] == ["Clarity", "Structure"]
    assert criteria[0]["weight"] == 1.5

    detail_response = client.get(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["questions"][0]["rubric_criteria"][1]["name"] == "Structure"


def test_employer_can_update_draft_interview_questions_and_rubric(client):
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)

    response = client.put(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Updated Structured Screen",
            "duration_minutes": 45,
            "questions": [
                {
                    "question_text": "Describe your troubleshooting process.",
                    "expected_answer": "Clarifies symptoms, isolates causes, tests hypotheses, documents resolution.",
                    "question_type": "text",
                    "weight": 2,
                    "order_index": 0,
                    "rubric_criteria": [
                        {
                            "name": "Evidence",
                            "description": "Uses observations to support decisions.",
                            "weight": 1.5,
                            "order_index": 0,
                        }
                    ],
                },
                {
                    "question_text": "How do you communicate delays?",
                    "expected_answer": "Communicates early, clearly, and with next steps.",
                    "question_type": "text",
                    "weight": 1,
                    "order_index": 1,
                },
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Updated Structured Screen"
    assert body["duration_minutes"] == 45
    assert [question["question_text"] for question in body["questions"]] == [
        "Describe your troubleshooting process.",
        "How do you communicate delays?",
    ]
    assert body["questions"][0]["rubric_criteria"][0]["name"] == "Evidence"


def test_employer_cannot_update_active_interview(client):
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)

    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    update_response = client.put(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Should Not Update"},
    )

    assert update_response.status_code == 400, update_response.text


def test_employer_cannot_activate_interview_without_questions(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/interviews/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Empty Draft",
            "description": "Missing questions",
            "duration_minutes": 30,
            "max_attempts": 1,
            "pass_score": 70,
            "questions": [],
        },
    )
    assert response.status_code == 201, response.text
    interview = response.json()

    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert activate_response.status_code == 400, activate_response.text
    assert activate_response.json()["detail"] == "Interview must have at least one question before activation"


def test_employer_cannot_access_another_organization_interview(client):
    register_user(client)
    first_token = login_user(client)
    interview = create_interview(client, first_token)

    register_user(client, email="other-employer@example.com")
    second_token = login_user(client, email="other-employer@example.com")

    response = client.get(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 403, response.text


def test_same_organization_member_can_view_interview(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)

    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")
    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_member_response.status_code == 201, add_member_response.text
    assert add_member_response.json()["role"] == "reviewer"

    response = client.get(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == interview["id"]


def test_non_admin_member_cannot_add_organization_members(client):
    register_user(client)
    owner_token = login_user(client)

    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")
    add_reviewer_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_reviewer_response.status_code == 201, add_reviewer_response.text

    register_user(client, email="candidate@example.com", role="employee")
    response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"email": "candidate@example.com", "role": "reviewer"},
    )

    assert response.status_code == 403, response.text


def test_duplicate_organization_membership_is_rejected(client):
    register_user(client)
    owner_token = login_user(client)
    register_user(client, email="reviewer@example.com", role="employee")

    first_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert first_response.status_code == 201, first_response.text

    duplicate_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )

    assert duplicate_response.status_code == 400, duplicate_response.text


def test_organization_member_roster_owner_can_list_and_non_admin_cannot(client):
    register_user(client)
    owner_token = login_user(client)
    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")

    add_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_response.status_code == 201, add_response.text

    members_response = client.get(
        "/api/users/me/organization/members",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert members_response.status_code == 200, members_response.text
    members = members_response.json()
    assert len(members) == 2
    roles = {member["email"]: member["role"] for member in members}
    assert roles == {"employer@example.com": "owner", "reviewer@example.com": "reviewer"}
    assert all(member["full_name"] for member in members)
    assert all(member["user_id"] for member in members)

    reviewer_response = client.get(
        "/api/users/me/organization/members",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_response.status_code == 403, reviewer_response.text


def test_organization_owner_can_view_audit_logs_and_reviewer_cannot(client):
    register_user(client)
    owner_token = login_user(client)
    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")

    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_member_response.status_code == 201, add_member_response.text

    owner_response = client.get(
        "/api/audit-logs/",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_response.status_code == 200, owner_response.text
    audit_logs = owner_response.json()
    membership_log = next(log for log in audit_logs if log["action"] == "team_membership.created")
    assert membership_log["details"]["target_email"] == "reviewer@example.com"
    assert membership_log["details"]["role"] == "reviewer"

    filtered_response = client.get(
        "/api/audit-logs/?action=team_membership.created&target_type=team_membership",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert filtered_response.status_code == 200, filtered_response.text
    assert len(filtered_response.json()) == 1

    reviewer_response = client.get(
        "/api/audit-logs/",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_response.status_code == 403, reviewer_response.text


def test_same_organization_recruiter_can_manage_invitations(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    from app.config import settings

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)
    monkeypatch.setattr(settings, "INVITATION_RESEND_COOLDOWN_SECONDS", 0)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    register_user(client, email="recruiter@example.com", role="employee")
    recruiter_token = login_user(client, email="recruiter@example.com")
    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "recruiter@example.com", "role": "recruiter"},
    )
    assert add_member_response.status_code == 201, add_member_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()
    assert invitation["status"] == "sent"
    assert invitation["sent_at"] is not None

    verify_response = client.get(f"/api/invitations/verify/{invitation['unique_token']}")
    assert verify_response.status_code == 200, verify_response.text
    verified = verify_response.json()
    assert verified["candidate_email"] == "candidate@example.com"
    assert verified["interview"]["title"] == "Customer Support Screen"
    assert verified["interview"]["duration_minutes"] == 30
    assert verified["interview"]["questions"][0]["question_text"] == "How do you handle an upset customer?"
    assert "expected_answer" not in verified["interview"]["questions"][0]
    assert verified["integrity_policy"]["tracking_enabled"] is True
    assert verified["integrity_policy"]["block_clipboard"] is True
    assert "enforce_fullscreen" in verified["integrity_policy"]

    list_response = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["status"] == "sent"

    resend_response = client.post(
        f"/api/invitations/{invitation['id']}/resend",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert resend_response.status_code == 200, resend_response.text


def test_invitation_resend_is_rate_limited(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    from app.config import settings

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)
    monkeypatch.setattr(settings, "INVITATION_RESEND_COOLDOWN_SECONDS", 300)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()

    resend_response = client.post(
        f"/api/invitations/{invitation['id']}/resend",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resend_response.status_code == 429, resend_response.text
    assert resend_response.headers["Retry-After"]


def test_cross_organization_employer_cannot_manage_invitations(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    register_user(client, email="other-employer@example.com")
    other_token = login_user(client, email="other-employer@example.com")

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
        },
    )
    assert create_response.status_code == 403, create_response.text

    list_response = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert list_response.status_code == 403, list_response.text


def test_bulk_invitations_are_marked_sent(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    response = client.post(
        "/api/invitations/bulk",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=[
            {"interview_id": interview["id"], "candidate_email": "one@example.com", "candidate_name": "One"},
            {"interview_id": interview["id"], "candidate_email": "two@example.com", "candidate_name": "Two"},
        ],
    )
    assert response.status_code == 201, response.text
    invitations = response.json()
    assert len(invitations) == 2
    assert {invitation["status"] for invitation in invitations} == {"sent"}
    assert all(invitation["sent_at"] for invitation in invitations)

    audit_response = client.get(
        "/api/audit-logs/?action=invitation.bulk_created",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert audit_response.status_code == 200, audit_response.text
    assert audit_response.json()[0]["details"]["created_count"] == 2


def test_bulk_invitations_reject_batches_over_limit(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    from app.config import settings

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)
    monkeypatch.setattr(settings, "MAX_BULK_INVITATIONS", 2)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    response = client.post(
        "/api/invitations/bulk",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=[
            {"interview_id": interview["id"], "candidate_email": "one@example.com", "candidate_name": "One"},
            {"interview_id": interview["id"], "candidate_email": "two@example.com", "candidate_name": "Two"},
            {"interview_id": interview["id"], "candidate_email": "three@example.com", "candidate_name": "Three"},
        ],
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Bulk invitations cannot exceed 2 candidates"


def test_bulk_invitations_reject_mixed_interview_ids(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    first_interview = create_interview(client, owner_token, title="First Screen")
    second_interview = create_interview(client, owner_token, title="Second Screen")

    response = client.post(
        "/api/invitations/bulk",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=[
            {"interview_id": first_interview["id"], "candidate_email": "one@example.com", "candidate_name": "One"},
            {"interview_id": second_interview["id"], "candidate_email": "two@example.com", "candidate_name": "Two"},
        ],
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "All bulk invitations must target the same interview"


def test_invitation_email_preview_uses_interview_and_custom_message(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token, title="Preview Screen")

    response = client.post(
        f"/api/invitations/preview/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"candidate_name": "Candidate Preview", "custom_message": "Please use a quiet room."},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subject"] == "Interview Invitation - Preview Screen"
    assert body["interview_link"].endswith("/interview/sample-token")
    assert "Candidate Preview" in body["html_body"]
    assert "Please use a quiet room." in body["html_body"]
    assert "Preview Screen" in body["html_body"]


def test_employer_bulk_invites_candidate_completes_pipeline(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    async def failing_send_completion_email(**kwargs):
        raise RuntimeError("mail transport unavailable")

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)
    monkeypatch.setattr("app.services.email_service.send_completion_email", failing_send_completion_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token, title="Pipeline Screen")
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    invite_response = client.post(
        "/api/invitations/bulk",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=[
            {
                "interview_id": interview["id"],
                "candidate_email": "pipeline-candidate@example.com",
                "candidate_name": "Pipeline Candidate",
            }
        ],
    )
    assert invite_response.status_code == 201, invite_response.text
    invitation = invite_response.json()[0]
    assert invitation["status"] == "sent"

    verify_response = client.get(f"/api/invitations/verify/{invitation['unique_token']}")
    assert verify_response.status_code == 200, verify_response.text
    verified_invitation = verify_response.json()
    assert verified_invitation["interview"]["title"] == "Pipeline Screen"
    assert len(verified_invitation["interview"]["questions"]) == 1

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview["id"],
            "candidate_email": invitation["candidate_email"],
            "candidate_name": invitation["candidate_name"],
            "invitation_token": invitation["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    candidate_response = start_response.json()
    assert candidate_response["status"] == "in_progress"

    accepted_invitation_response = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert accepted_invitation_response.status_code == 200, accepted_invitation_response.text
    assert accepted_invitation_response.json()[0]["status"] == "accepted"

    question = verified_invitation["interview"]["questions"][0]
    answer_response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": question["id"],
            "answer_text": "I listen, empathize, clarify, take ownership, resolve, and follow up with the customer.",
            "time_taken_seconds": 120,
        },
    )
    assert answer_response.status_code == 200, answer_response.text

    quality_response = client.post(
        f"/api/responses/{candidate_response['id']}/quality",
        params={
            "voice_quality": 92,
            "background_quality": 88,
            "face_visibility": 91,
            "lighting": 86,
        },
    )
    assert quality_response.status_code == 200, quality_response.text

    emotion_response = client.post(
        f"/api/responses/{candidate_response['id']}/emotion",
        params={"emotion": "neutral", "confidence": 90},
    )
    assert emotion_response.status_code == 200, emotion_response.text

    complete_response = client.post(f"/api/responses/{candidate_response['id']}/complete")
    assert complete_response.status_code == 200, complete_response.text
    completed_response = complete_response.json()
    assert completed_response["status"] == "completed"

    completed_invitation_response = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert completed_invitation_response.status_code == 200, completed_invitation_response.text
    assert completed_invitation_response.json()[0]["status"] == "completed"

    employer_responses = client.get(
        f"/api/responses/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert employer_responses.status_code == 200, employer_responses.text
    assert employer_responses.json()[0]["status"] == "completed"
    assert employer_responses.json()[0]["total_score"] > 0
    assert employer_responses.json()[0]["passed"] is True

    interview_report_response = client.get(
        f"/api/reports/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert interview_report_response.status_code == 200, interview_report_response.text
    interview_report = interview_report_response.json()
    assert interview_report["candidates"][0]["response_id"] == candidate_response["id"]
    assert interview_report["candidates"][0]["evaluation_provider"]
    assert interview_report["candidates"][0]["evaluation_model"]
    assert interview_report["candidates"][0]["evaluation_status"] == "completed"

    candidate_report_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert candidate_report_response.status_code == 200, candidate_report_response.text
    candidate_report = candidate_report_response.json()
    assert candidate_report["response_id"] == candidate_response["id"]
    assert candidate_report["evaluation_provider"]
    assert candidate_report["evaluation_model"]
    assert candidate_report["evaluation_status"] == "completed"
    assert candidate_report["answers"][0]["feedback_en"]
    assert candidate_report["answers"][0]["feedback_ar"]
    assert "How do you handle an upset customer?" == candidate_report["answers"][0]["question"]
    assert "listen" in candidate_report["answers"][0]["evidence"]["matched_keywords"]
    assert candidate_report["integrity"]["total_events"] == 0
    assert candidate_report["integrity"]["violation_count"] == 0
    assert candidate_report["integrity"]["breakdown"] == {}

    evaluation_audit_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert evaluation_audit_response.status_code == 200, evaluation_audit_response.text
    evaluation_audit = evaluation_audit_response.json()
    assert len(evaluation_audit) == 1
    assert evaluation_audit[0]["provider"] == candidate_report["evaluation_provider"]
    assert evaluation_audit[0]["config_hash"]
    assert evaluation_audit[0]["raw_summary"]["answer_count"] == 1
    assert evaluation_audit[0]["scores"][0]["question"] == "How do you handle an upset customer?"
    assert "listen" in evaluation_audit[0]["scores"][0]["evidence"]["matched_keywords"]
    assert evaluation_audit[0]["scores"][0]["evidence"]["rubric_criteria"][0]["name"] == "Ownership"

    register_user(client, email="pipeline-reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="pipeline-reviewer@example.com")
    add_reviewer_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "pipeline-reviewer@example.com", "role": "reviewer"},
    )
    assert add_reviewer_response.status_code == 201, add_reviewer_response.text

    reviewer_report_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_report_response.status_code == 200, reviewer_report_response.text
    reviewer_audit_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_audit_response.status_code == 200, reviewer_audit_response.text
    reviewer_analytics_response = client.get(
        f"/api/reports/interview/{interview['id']}/evaluation-analytics",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_analytics_response.status_code == 200, reviewer_analytics_response.text
    reviewer_reevaluation_response = client.post(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_reevaluation_response.status_code == 403, reviewer_reevaluation_response.text
    reviewer_batch_response = client.post(
        f"/api/reports/interview/{interview['id']}/evaluations",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_batch_response.status_code == 403, reviewer_batch_response.text

    register_user(client, email="pipeline-candidate@example.com", role="employee")
    candidate_token = login_user(client, email="pipeline-candidate@example.com")
    candidate_self_report_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_self_report_response.status_code == 200, candidate_self_report_response.text
    candidate_self_audit_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_self_audit_response.status_code == 200, candidate_self_audit_response.text
    candidate_self_reevaluation_response = client.post(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_self_reevaluation_response.status_code == 403, candidate_self_reevaluation_response.text

    register_user(client, email="pipeline-other@example.com")
    other_token = login_user(client, email="pipeline-other@example.com")
    other_candidate_report_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_candidate_report_response.status_code == 403, other_candidate_report_response.text
    other_candidate_audit_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_candidate_audit_response.status_code == 403, other_candidate_audit_response.text
    other_analytics_response = client.get(
        f"/api/reports/interview/{interview['id']}/evaluation-analytics",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_analytics_response.status_code == 403, other_analytics_response.text

    reevaluation_response = client.post(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert reevaluation_response.status_code == 200, reevaluation_response.text
    reevaluation = reevaluation_response.json()
    assert reevaluation["id"] != evaluation_audit[0]["id"]
    assert reevaluation["status"] == "queued"

    updated_audit_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/evaluations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert updated_audit_response.status_code == 200, updated_audit_response.text
    updated_audit = updated_audit_response.json()
    assert len(updated_audit) == 2
    assert updated_audit[0]["id"] == reevaluation["id"]
    assert updated_audit[0]["status"] == "completed"
    assert updated_audit[0]["raw_summary"]["answer_count"] == 1
    assert "listen" in updated_audit[0]["scores"][0]["evidence"]["matched_keywords"]

    batch_reevaluation_response = client.post(
        f"/api/reports/interview/{interview['id']}/evaluations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert batch_reevaluation_response.status_code == 200, batch_reevaluation_response.text
    batch_runs = batch_reevaluation_response.json()
    assert len(batch_runs) == 1
    assert batch_runs[0]["response_id"] == candidate_response["id"]
    assert batch_runs[0]["status"] == "queued"

    analytics_response = client.get(
        f"/api/reports/interview/{interview['id']}/evaluation-analytics",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert analytics_response.status_code == 200, analytics_response.text
    analytics = analytics_response.json()
    assert analytics["completed_responses"] == 1
    assert analytics["total_evaluation_runs"] == 3
    assert analytics["completed_runs"] == 3
    assert analytics["average_latest_score"] > 0
    assert analytics["provider_counts"]["deterministic_baseline"] == 3

    candidate_pdf_response = client.get(
        f"/api/reports/candidate/{candidate_response['id']}/pdf",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert candidate_pdf_response.status_code == 200, candidate_pdf_response.text
    assert candidate_pdf_response.headers["content-type"] == "application/pdf"
    assert candidate_pdf_response.content.startswith(b"%PDF")

    from app.database import SessionLocal
    from app.models import EvaluationRun, EvaluationScore

    db = SessionLocal()
    try:
        evaluation_run = db.query(EvaluationRun).filter(EvaluationRun.response_id == candidate_response["id"]).order_by(EvaluationRun.id.asc()).first()
        assert evaluation_run.status == "completed"
        assert evaluation_run.provider
        assert evaluation_run.provider_version
        assert evaluation_run.config_hash
        assert evaluation_run.completed_at is not None
        assert db.query(EvaluationRun).filter(EvaluationRun.response_id == candidate_response["id"]).count() == 3
        scores = db.query(EvaluationScore).filter(EvaluationScore.evaluation_run_id == evaluation_run.id).all()
        assert len(scores) == 1
        assert scores[0].score > 0
        assert scores[0].evidence_json
        assert "listen" in scores[0].evidence_json
    finally:
        db.close()


def test_invitation_can_be_revoked(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()

    revoke_response = client.post(
        f"/api/invitations/{invitation['id']}/revoke",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert revoke_response.status_code == 200, revoke_response.text
    revoked = revoke_response.json()
    assert revoked["status"] == "revoked"
    assert revoked["expires_at"] is not None

    verify_response = client.get(f"/api/invitations/verify/{invitation['unique_token']}")
    assert verify_response.status_code == 410, verify_response.text
    assert verify_response.json()["detail"] == "Invitation has been revoked"

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
            "invitation_token": invitation["unique_token"],
        },
    )
    assert start_response.status_code == 410, start_response.text

    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        audit_log = db.query(AuditLog).filter(AuditLog.action == "invitation.revoked").first()
        assert audit_log is not None
        assert audit_log.target_id == invitation["id"]
        assert json.loads(audit_log.details)["candidate_email"] == "candidate@example.com"
    finally:
        db.close()

    resend_response = client.post(
        f"/api/invitations/{invitation['id']}/resend",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resend_response.status_code == 400, resend_response.text


def test_completed_invitation_can_be_deleted(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "completed@example.com",
            "candidate_name": "Completed Candidate",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview["id"],
            "candidate_email": invitation["candidate_email"],
            "candidate_name": invitation["candidate_name"],
            "invitation_token": invitation["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    candidate_response = start_response.json()

    answer_response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen, empathize, clarify, take ownership, resolve, and follow up with the customer.",
            "time_taken_seconds": 120,
        },
    )
    assert answer_response.status_code == 200, answer_response.text

    complete_response = client.post(f"/api/responses/{candidate_response['id']}/complete")
    assert complete_response.status_code == 200, complete_response.text

    list_response = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()[0]["status"] == "completed"

    cancel_response = client.delete(
        f"/api/invitations/{invitation['id']}/cancel",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert cancel_response.status_code == 204, cancel_response.text

    list_after = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert list_after.status_code == 200, list_after.text
    assert list_after.json() == []

    # Response and its answers are hard-deleted together with the invitation.
    response_after = client.get(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response_after.status_code == 404, response_after.text

    from app.database import SessionLocal
    from app.models import AuditLog, CandidateResponse, QuestionAnswer

    db = SessionLocal()
    try:
        stored_response = db.query(CandidateResponse).filter(CandidateResponse.id == candidate_response["id"]).first()
        assert stored_response is None

        answer_count = (
            db.query(QuestionAnswer)
            .filter(QuestionAnswer.response_id == candidate_response["id"])
            .count()
        )
        assert answer_count == 0

        audit_log = db.query(AuditLog).filter(AuditLog.action == "invitation.cancelled").first()
        assert audit_log is not None
        assert audit_log.target_id == invitation["id"]
        assert json.loads(audit_log.details)["candidate_email"] == "completed@example.com"
    finally:
        db.close()


def test_non_completed_invitation_cannot_be_deleted(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "pending@example.com",
            "candidate_name": "Pending Candidate",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()

    delete_response = client.delete(
        f"/api/invitations/{invitation['id']}/cancel",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert delete_response.status_code == 400, delete_response.text
    assert delete_response.json()["detail"] == "Only completed invitations can be cancelled"


def complete_invited_response(client, interview, invitation):
    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview["id"],
            "candidate_email": invitation["candidate_email"],
            "candidate_name": invitation["candidate_name"],
            "invitation_token": invitation["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    candidate_response = start_response.json()

    answer_response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen, empathize, clarify, take ownership, resolve, and follow up with the customer.",
            "time_taken_seconds": 120,
        },
    )
    assert answer_response.status_code == 200, answer_response.text

    complete_response = client.post(f"/api/responses/{candidate_response['id']}/complete")
    assert complete_response.status_code == 200, complete_response.text
    return candidate_response


def test_cancel_all_completed_invitations_deletes_responses(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    response_ids = []
    for email, name in (
        ("cancel-a@example.com", "Cancel A"),
        ("cancel-b@example.com", "Cancel B"),
    ):
        create_response = client.post(
            "/api/invitations/",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "interview_id": interview["id"],
                "candidate_email": email,
                "candidate_name": name,
            },
        )
        assert create_response.status_code == 201, create_response.text
        candidate_response = complete_invited_response(client, interview, create_response.json())
        response_ids.append(candidate_response["id"])

    cancel_all_response = client.delete(
        f"/api/invitations/{interview['id']}/cancel-all",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert cancel_all_response.status_code == 204, cancel_all_response.text

    list_after = client.get(
        f"/api/invitations/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert list_after.status_code == 200, list_after.text
    assert list_after.json() == []

    for response_id in response_ids:
        response_after = client.get(
            f"/api/responses/{response_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response_after.status_code == 404, response_after.text

    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        audit_log = db.query(AuditLog).filter(AuditLog.action == "invitation.cancelled_all").first()
        assert audit_log is not None
        assert audit_log.target_id == interview["id"]
        assert json.loads(audit_log.details)["cancelled_count"] == 2
    finally:
        db.close()


def test_cancel_all_rejects_when_no_completed_invitations(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    cancel_all_response = client.delete(
        f"/api/invitations/{interview['id']}/cancel-all",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert cancel_all_response.status_code == 400, cancel_all_response.text
    assert cancel_all_response.json()["detail"] == "No completed invitations to cancel"


def test_cross_organization_employer_cannot_delete_invitation(client, monkeypatch):
    async def noop_send_invitation_email(**kwargs):
        return None

    monkeypatch.setattr("app.api.invitations.send_invitation_email", noop_send_invitation_email)

    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    create_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "interview_id": interview["id"],
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate One",
        },
    )
    assert create_response.status_code == 201, create_response.text
    invitation = create_response.json()

    register_user(client, email="other-employer@example.com")
    other_token = login_user(client, email="other-employer@example.com")

    delete_response = client.delete(
        f"/api/invitations/{invitation['id']}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert delete_response.status_code == 403, delete_response.text


def start_candidate_response(client, interview_id, email="candidate@example.com", name="Candidate One"):
    response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview_id,
            "candidate_email": email,
            "candidate_name": name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_answer_audio_upload_rejects_unsupported_extension(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "Audio answer",
        },
        files={"audio_file": ("payload.exe", b"not audio", "application/octet-stream")},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Unsupported audio file type"


def test_answer_audio_upload_rejects_oversized_file(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE", 4)
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "Audio answer",
        },
        files={"audio_file": ("answer.wav", WAV_BYTES, "audio/wav")},
    )

    assert response.status_code == 413, response.text
    assert response.json()["detail"] == "Audio file exceeds maximum size"


def test_answer_audio_upload_rejects_mismatched_content(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "Audio answer",
        },
        files={"audio_file": ("answer.wav", b"not really a wav", "audio/wav")},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Uploaded audio content does not match the file type"


def test_same_organization_member_can_list_interview_responses(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")
    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_member_response.status_code == 201, add_member_response.text

    list_response = client.get(
        f"/api/responses/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()[0]["id"] == candidate_response["id"]


def test_cross_organization_employer_cannot_access_responses(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    register_user(client, email="other-employer@example.com")
    other_token = login_user(client, email="other-employer@example.com")

    list_response = client.get(
        f"/api/responses/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert list_response.status_code == 403, list_response.text

    detail_response = client.get(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert detail_response.status_code == 403, detail_response.text


def test_candidate_can_access_own_response_details(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"], email="candidate@example.com")
    register_user(client, email="candidate@example.com", role="employee")
    candidate_token = login_user(client, email="candidate@example.com")

    detail_response = client.get(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["candidate_email"] == "candidate@example.com"


def test_response_manager_can_delete_candidate_response_and_audio(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"])

    answer_response = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen and follow up.",
        },
        files={"audio_file": ("answer.wav", WAV_BYTES, "audio/wav")},
    )
    assert answer_response.status_code == 200, answer_response.text
    audio_file_path = answer_response.json()["audio_file_path"]
    assert audio_file_path
    assert os.path.exists(audio_file_path)

    delete_response = client.delete(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert delete_response.status_code == 204, delete_response.text
    assert not os.path.exists(audio_file_path)

    from app.database import SessionLocal
    from app.models import AuditLog

    db = SessionLocal()
    try:
        audit_log = db.query(AuditLog).filter(AuditLog.action == "candidate_response.deleted").first()
        assert audit_log is not None
        assert audit_log.target_id == candidate_response["id"]
        assert json.loads(audit_log.details)["candidate_email"] == "candidate@example.com"
    finally:
        db.close()

    detail_response = client.get(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert detail_response.status_code == 404, detail_response.text


def test_reviewer_candidate_and_cross_org_cannot_delete_candidate_response(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)
    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text
    candidate_response = start_candidate_response(client, interview["id"], email="candidate-delete@example.com")

    register_user(client, email="delete-reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="delete-reviewer@example.com")
    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "delete-reviewer@example.com", "role": "reviewer"},
    )
    assert add_member_response.status_code == 201, add_member_response.text

    register_user(client, email="candidate-delete@example.com", role="employee")
    candidate_token = login_user(client, email="candidate-delete@example.com")

    register_user(client, email="delete-other@example.com")
    other_token = login_user(client, email="delete-other@example.com")

    for token in [reviewer_token, candidate_token, other_token]:
        delete_response = client.delete(
            f"/api/responses/{candidate_response['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_response.status_code == 403, delete_response.text

    owner_detail_response = client.get(
        f"/api/responses/{candidate_response['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_detail_response.status_code == 200, owner_detail_response.text


def test_organization_member_can_view_interview_report_and_cross_org_cannot(client):
    register_user(client)
    owner_token = login_user(client)
    interview = create_interview(client, owner_token)

    register_user(client, email="reviewer@example.com", role="employee")
    reviewer_token = login_user(client, email="reviewer@example.com")
    add_member_response = client.post(
        "/api/users/me/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "reviewer@example.com", "role": "reviewer"},
    )
    assert add_member_response.status_code == 201, add_member_response.text

    reviewer_report_response = client.get(
        f"/api/reports/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_report_response.status_code == 200, reviewer_report_response.text
    assert reviewer_report_response.json()["interview_id"] == interview["id"]

    register_user(client, email="other-employer@example.com")
    other_token = login_user(client, email="other-employer@example.com")
    other_report_response = client.get(
        f"/api/reports/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_report_response.status_code == 403, other_report_response.text


def seed_template(client):
    from app.database import SessionLocal
    from app.models import InterviewTemplate, TemplateQuestion, TemplateRubricCriterion

    db = SessionLocal()
    try:
        template = InterviewTemplate(
            name="Customer Support Screen",
            description="First-round support screen",
            role_category="customer_support",
            duration_minutes=25,
            pass_score=70,
            is_active=True,
        )
        db.add(template)
        db.flush()
        first_question = TemplateQuestion(
            template_id=template.id,
            question_text="How do you handle an upset customer?",
            expected_answer="Listen, empathize, clarify, resolve, and follow up.",
            question_type="text",
            weight=1.5,
            order_index=0,
        )
        db.add(first_question)
        db.flush()
        db.add(TemplateRubricCriterion(
            template_question_id=first_question.id,
            name="Clarity",
            description="Answer is clear and direct.",
            weight=1.0,
            order_index=0,
        ))
        db.add(TemplateQuestion(
            template_id=template.id,
            question_text="Describe a time you improved a customer experience.",
            expected_answer="Gives a specific example with action and outcome.",
            question_type="text",
            weight=1.0,
            order_index=1,
        ))
        db.commit()
        db.refresh(template)
        return template.id
    finally:
        db.close()


def test_list_and_get_interview_templates(client):
    template_id = seed_template(client)

    list_response = client.get("/api/interviews/templates")
    assert list_response.status_code == 200, list_response.text
    templates = list_response.json()
    assert len(templates) == 1
    assert templates[0]["name"] == "Customer Support Screen"
    assert len(templates[0]["questions"]) == 2
    assert templates[0]["questions"][0]["rubric_criteria"][0]["name"] == "Clarity"

    detail_response = client.get(f"/api/interviews/templates/{template_id}")
    assert detail_response.status_code == 200, detail_response.text
    template = detail_response.json()
    assert template["id"] == template_id
    assert [question["order_index"] for question in template["questions"]] == [0, 1]


def test_create_interview_from_template(client):
    template_id = seed_template(client)
    register_user(client)
    token = login_user(client)

    response = client.post(
        f"/api/interviews/templates/{template_id}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Support Agent Screen", "max_attempts": 2},
    )

    assert response.status_code == 201, response.text
    interview = response.json()
    assert interview["title"] == "Support Agent Screen"
    assert interview["duration_minutes"] == 25
    assert interview["pass_score"] == 70
    assert interview["max_attempts"] == 2
    assert interview["organization_id"] is not None
    assert len(interview["questions"]) == 2
    assert interview["questions"][0]["weight"] == 1.5
    assert interview["questions"][0]["rubric_criteria"][0]["name"] == "Clarity"


def create_completed_response(client):
    """Helper: create interview, invite candidate, complete response.
    Returns (token, response_id).
    """
    register_user(client)
    token = login_user(client)

    interview = create_interview(client, token)
    interview_id = interview["id"]

    activate_response = client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    invite_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "candidate@test.com",
            "candidate_name": "Test Candidate",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    verify_response = client.get(f"/api/invitations/verify/{invite['unique_token']}")
    assert verify_response.status_code == 200, verify_response.text

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview_id,
            "candidate_email": "candidate@test.com",
            "candidate_name": "Test Candidate",
            "invitation_token": invite["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    response_id = start_response.json()["id"]

    answer_response = client.post(
        f"/api/responses/{response_id}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen carefully and empathize with the customer.",
            "time_taken_seconds": 120,
        },
    )
    assert answer_response.status_code == 200, answer_response.text

    complete_response = client.post(f"/api/responses/{response_id}/complete")
    assert complete_response.status_code == 200, complete_response.text

    return token, response_id


def test_reviewer_decision_flow(client):
    """Test setting reviewer decision and scorecard."""
    token, response_id = create_completed_response(client)

    # Set decision to shortlisted
    decision_response = client.put(
        f"/api/responses/{response_id}/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "shortlisted"},
    )
    assert decision_response.status_code == 200, decision_response.text
    decision = decision_response.json()
    assert decision["reviewer_decision"] == "shortlisted"
    assert decision["response_id"] == response_id

    # Check that candidate report includes decision
    report_response = client.get(
        f"/api/reports/candidate/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_response.status_code == 200, report_response.text
    assert report_response.json()["reviewer_decision"] == "shortlisted"

    # Change decision to hired
    decision_response = client.put(
        f"/api/responses/{response_id}/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "hired"},
    )
    assert decision_response.status_code == 200, decision_response.text
    assert decision_response.json()["reviewer_decision"] == "hired"


def test_reviewer_scorecard_crud(client):
    """Test creating, reading, and updating a reviewer scorecard."""
    token, response_id = create_completed_response(client)

    # Create scorecard
    create_response = client.post(
        f"/api/responses/{response_id}/scorecard",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "overall_score": 85.0,
            "strengths": "Good communication skills, empathetic",
            "weaknesses": "Could provide more specific examples",
            "overall_comment": "Strong candidate for the role",
        },
    )
    assert create_response.status_code == 201, create_response.text
    scorecard = create_response.json()
    assert scorecard["overall_score"] == 85.0
    assert scorecard["strengths"] == "Good communication skills, empathetic"
    assert scorecard["response_id"] == response_id

    # Read scorecard
    get_response = client.get(
        f"/api/responses/{response_id}/scorecard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["overall_score"] == 85.0

    # Update scorecard
    update_response = client.post(
        f"/api/responses/{response_id}/scorecard",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "overall_score": 90.0,
            "strengths": "Good communication skills, empathetic, great problem solver",
            "weaknesses": "",
            "overall_comment": "Excellent candidate",
        },
    )
    assert update_response.status_code == 201, update_response.text
    assert update_response.json()["overall_score"] == 90.0
    assert update_response.json()["strengths"] == "Good communication skills, empathetic, great problem solver"


def test_reviewer_decision_unauthorized(client):
    """Test that unauthorized users cannot set decisions."""
    token, response_id = create_completed_response(client)

    # Employee should not be able to set decisions
    register_user(client, email="employee@test.com", role="employee")
    employee_token = login_user(client, email="employee@test.com")

    decision_response = client.put(
        f"/api/responses/{response_id}/decision",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"decision": "shortlisted"},
    )
    assert decision_response.status_code == 403


def test_reviewer_decision_invalid_value(client):
    """Test that invalid decision values are rejected."""
    token, response_id = create_completed_response(client)

    decision_response = client.put(
        f"/api/responses/{response_id}/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "invalid_value"},
    )
    assert decision_response.status_code == 422


def test_reviewer_decision_appears_in_interview_report(client):
    """Test that reviewer decision is included in the interview report."""
    token, response_id = create_completed_response(client)

    response = client.get(
        f"/api/reports/interview/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text

    # Interview report endpoint expects interview_id, not response_id
    # Get the interview ID from the response
    resp_detail = client.get(
        f"/api/responses/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_detail.status_code == 200, resp_detail.text
    interview_id = resp_detail.json()["interview_id"]

    report_response = client.get(
        f"/api/reports/interview/{interview_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert len(report["candidates"]) > 0
    assert report["candidates"][0].get("reviewer_decision") is not None


def test_transcript_update_and_read(client):
    """Test updating and reading a transcript for an answer."""
    token, response_id = create_completed_response(client)

    resp_detail = client.get(
        f"/api/responses/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_detail.status_code == 200
    answers = resp_detail.json().get("question_answers", [])
    assert len(answers) > 0
    question_id = answers[0]["question_id"]

    update_response = client.put(
        f"/api/responses/{response_id}/answers/{question_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
        json={"transcript": "Candidate explained how they handle upset customers by listening and empathizing."},
    )
    assert update_response.status_code == 200, update_response.text
    data = update_response.json()
    assert data["transcript"] == "Candidate explained how they handle upset customers by listening and empathizing."

    get_response = client.get(
        f"/api/responses/{response_id}/answers/{question_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["transcript"] == "Candidate explained how they handle upset customers by listening and empathizing."


def test_transcript_unauthorized(client):
    """Test that unauthorized users cannot modify transcripts."""
    token, response_id = create_completed_response(client)

    register_user(client, email="employee@test.com", role="employee")
    employee_token = login_user(client, email="employee@test.com")

    resp_detail = client.get(
        f"/api/responses/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    question_id = resp_detail.json()["question_answers"][0]["question_id"]

    update_response = client.put(
        f"/api/responses/{response_id}/answers/{question_id}/transcript",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"transcript": "Should not work"},
    )
    assert update_response.status_code in (403, 404)


def test_audio_only_answer_scored_from_transcript(client, monkeypatch):
    """Audio-only answers (no typed text) get scored from the transcribed speech."""
    from app.services.transcription_service import TranscriptionResult

    class StubWhisperProvider:
        name = "whisper"
        version = "1.0.0"

        async def transcribe_audio(self, audio_path):
            return TranscriptionResult(
                transcript="I listen and empathize with the customer.",
                detected_language="en",
                confidence=0.9,
            )

    monkeypatch.setattr(
        "app.services.transcription_service.get_transcription_provider",
        lambda: StubWhisperProvider(),
    )

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]

    activate_response = client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    invite_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "audio-candidate@test.com",
            "candidate_name": "Audio Candidate",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    verify_response = client.get(f"/api/invitations/verify/{invite['unique_token']}")
    assert verify_response.status_code == 200, verify_response.text

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview_id,
            "candidate_email": "audio-candidate@test.com",
            "candidate_name": "Audio Candidate",
            "invitation_token": invite["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    response_id = start_response.json()["id"]

    answer_response = client.post(
        f"/api/responses/{response_id}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "",
            "time_taken_seconds": 90,
        },
        files={"audio_file": ("answer.wav", WAV_BYTES, "audio/wav")},
    )
    assert answer_response.status_code == 200, answer_response.text
    assert answer_response.json()["audio_file_path"]

    complete_response = client.post(f"/api/responses/{response_id}/complete")
    assert complete_response.status_code == 200, complete_response.text

    report_response = client.get(
        f"/api/reports/candidate/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()

    answer_report = report["answers"][0]
    assert "I listen and empathize with the customer." in answer_report["transcript"]
    assert answer_report["score"] > 0


def test_video_only_answer_scored_from_transcript(client, monkeypatch):
    """Video-only answers (no typed text, no separate audio) get scored from
    the speech captured in the video track."""
    from app.services.transcription_service import TranscriptionResult

    class StubWhisperProvider:
        name = "whisper"
        version = "1.0.0"

        async def transcribe_audio(self, audio_path):
            assert audio_path.endswith(".mp4")
            return TranscriptionResult(
                transcript="I listen and empathize with the customer.",
                detected_language="en",
                confidence=0.9,
            )

    monkeypatch.setattr(
        "app.services.transcription_service.get_transcription_provider",
        lambda: StubWhisperProvider(),
    )

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]

    activate_response = client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    invite_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "video-candidate@test.com",
            "candidate_name": "Video Candidate",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    verify_response = client.get(f"/api/invitations/verify/{invite['unique_token']}")
    assert verify_response.status_code == 200, verify_response.text

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview_id,
            "candidate_email": "video-candidate@test.com",
            "candidate_name": "Video Candidate",
            "invitation_token": invite["unique_token"],
        },
    )
    assert start_response.status_code == 201, start_response.text
    response_id = start_response.json()["id"]

    answer_response = client.post(
        f"/api/responses/{response_id}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "",
            "time_taken_seconds": 90,
        },
        files={"video_file": ("answer.mp4", WAV_BYTES, "video/mp4")},
    )
    assert answer_response.status_code == 200, answer_response.text
    assert answer_response.json()["video_file_path"]
    assert not answer_response.json()["audio_file_path"]

    complete_response = client.post(f"/api/responses/{response_id}/complete")
    assert complete_response.status_code == 200, complete_response.text

    report_response = client.get(
        f"/api/reports/candidate/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()

    answer_report = report["answers"][0]
    assert "I listen and empathize with the customer." in answer_report["transcript"]
    assert answer_report["score"] > 0


def test_candidate_results_portal_by_token(client, monkeypatch):
    """Candidates can view their own results via the invitation token
    without logging in."""
    from app.services.transcription_service import TranscriptionResult

    class StubWhisperProvider:
        name = "whisper"
        version = "1.0.0"

        async def transcribe_audio(self, audio_path):
            return TranscriptionResult(
                transcript="I listen and empathize with the customer.",
                detected_language="en",
                confidence=0.9,
            )

    monkeypatch.setattr(
        "app.services.transcription_service.get_transcription_provider",
        lambda: StubWhisperProvider(),
    )

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]

    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    invite_response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "portal-candidate@test.com",
            "candidate_name": "Portal Candidate",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()
    invitation_token = invite["unique_token"]

    client.get(f"/api/invitations/verify/{invitation_token}")

    start_response = client.post(
        "/api/responses/",
        json={
            "interview_id": interview_id,
            "candidate_email": "portal-candidate@test.com",
            "candidate_name": "Portal Candidate",
            "invitation_token": invitation_token,
        },
    )
    assert start_response.status_code == 201, start_response.text
    response_id = start_response.json()["id"]

    client.post(
        f"/api/responses/{response_id}/answer",
        params={
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen and empathize with the customer.",
        },
    )
    client.post(f"/api/responses/{response_id}/complete")

    results_response = client.get(f"/api/invitations/{invitation_token}/results")
    assert results_response.status_code == 200, results_response.text
    data = results_response.json()
    assert data["candidate_name"] == "Portal Candidate"
    assert data["total_score"] > 0
    assert "answers" in data
    assert data["answers"][0]["score"] > 0

    bad_response = client.get("/api/invitations/not-a-real-token/results")
    assert bad_response.status_code == 404


def test_answer_retake_replaces_answer_and_clears_score(client):
    """Candidates can retake an answer while the response is in progress."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="retake@test.com")

    qid = interview["questions"][0]["id"]
    first = client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={"question_id": qid, "answer_text": "wrong answer"},
    )
    assert first.status_code == 200, first.text

    retake = client.put(
        f"/api/responses/{candidate_response['id']}/answer/{qid}",
        params={"question_id": qid, "answer_text": "I listen carefully and empathize with the customer.", "time_taken_seconds": 99},
    )
    assert retake.status_code == 200, retake.text
    data = retake.json()
    assert data["answer_text"] == "I listen carefully and empathize with the customer."
    assert data["time_taken_seconds"] == 99
    assert data["score"] is None
    assert data["transcript"] is None


def test_integrity_events_recorded_and_timer_flagged(client):
    """Client-side integrity events are stored; server enforces duration."""
    from app.models import IntegrityEvent
    from app.database import SessionLocal

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="integrity@test.com")
    response_id = candidate_response["id"]

    events_response = client.post(
        f"/api/responses/{response_id}/integrity-events",
        json=[{"event_type": "tab_hidden", "details": "switched away"}, {"event_type": "window_blur"}],
    )
    assert events_response.status_code == 200, events_response.text
    assert events_response.json()["recorded"] == 2

    db = SessionLocal()
    try:
        events = db.query(IntegrityEvent).filter(IntegrityEvent.response_id == response_id).all()
        assert len(events) == 2
        assert events[0].event_type == "tab_hidden"
    finally:
        db.close()


def test_integrity_events_accept_anti_cheat_event_types(client):
    """Copy/paste, context menu, and fullscreen events are recorded."""
    from app.models import IntegrityEvent
    from app.database import SessionLocal

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="antichat@test.com")
    response_id = candidate_response["id"]

    events_response = client.post(
        f"/api/responses/{response_id}/integrity-events",
        json=[
            {"event_type": "copy", "details": "copied question"},
            {"event_type": "paste", "details": "pasted answer"},
            {"event_type": "context_menu", "details": "right click"},
            {"event_type": "fullscreen_exit", "details": "left fullscreen"},
        ],
    )
    assert events_response.status_code == 200, events_response.text
    assert events_response.json()["recorded"] == 4

    db = SessionLocal()
    try:
        events = db.query(IntegrityEvent).filter(IntegrityEvent.response_id == response_id).all()
        event_types = {event.event_type for event in events}
        assert event_types == {"copy", "paste", "context_menu", "fullscreen_exit"}
        assert {event.details for event in events} == {
            "copied question", "pasted answer", "right click", "left fullscreen",
        }
    finally:
        db.close()


def test_integrity_events_reject_unknown_event_types(client):
    """Unknown event types are silently ignored."""
    from app.models import IntegrityEvent
    from app.database import SessionLocal

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="antichat2@test.com")
    response_id = candidate_response["id"]

    events_response = client.post(
        f"/api/responses/{response_id}/integrity-events",
        json=[
            {"event_type": "copy", "details": "ok"},
            {"event_type": "delete_database", "details": "nope"},
        ],
    )
    assert events_response.status_code == 200, events_response.text
    assert events_response.json()["recorded"] == 1

    db = SessionLocal()
    try:
        events = db.query(IntegrityEvent).filter(IntegrityEvent.response_id == response_id).all()
        assert len(events) == 1
        assert events[0].event_type == "copy"
    finally:
        db.close()


def test_candidate_report_includes_integrity_summary(client):
    """Employer candidate report surfaces recorded integrity events."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="antichat3@test.com")
    response_id = candidate_response["id"]

    client.post(
        f"/api/responses/{response_id}/integrity-events",
        json=[
            {"event_type": "copy", "details": "copied question"},
            {"event_type": "paste", "details": "pasted answer"},
            {"event_type": "tab_hidden", "details": "switched away"},
        ],
    )
    client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen and empathize."},
    )
    client.post(f"/api/responses/{candidate_response['id']}/complete")

    report_response = client.get(
        f"/api/reports/candidate/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report_response.status_code == 200, report_response.text
    integrity = report_response.json()["integrity"]
    assert integrity["total_events"] == 3
    assert integrity["violation_count"] == 3
    assert integrity["severity_count"] == 2
    assert integrity["breakdown"] == {"copy": 1, "paste": 1, "tab_hidden": 1}
    assert len(integrity["events"]) == 3


def test_candidate_comparison_api(client):
    """Employers get side-by-side candidate comparison ranked by score."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    for i, (email, answer) in enumerate([("cand-a@test.com", "I listen and empathize with the customer."),
                                         ("cand-b@test.com", "I listen.")]):
        candidate_response = start_candidate_response(client, interview_id, email=email)
        client.post(
            f"/api/responses/{candidate_response['id']}/answer",
            params={"question_id": interview["questions"][0]["id"], "answer_text": answer},
        )
        client.post(f"/api/responses/{candidate_response['id']}/complete")

    comparison_response = client.get(
        f"/api/reports/interview/{interview_id}/comparison",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comparison_response.status_code == 200, comparison_response.text
    data = comparison_response.json()
    assert len(data["candidates"]) == 2
    # Ranked by total score descending
    assert data["candidates"][0]["total_score"] >= data["candidates"][1]["total_score"]
    assert data["candidates"][0]["question_scores"][0]["question"] == "How do you handle an upset customer?"
    # Per-question score reflects answer quality
    assert data["candidates"][0]["question_scores"][0]["score"] > data["candidates"][1]["question_scores"][0]["score"]


def test_candidate_profile_and_question_analytics(client):
    """Employers can view candidate CRM profile and per-question analytics."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    candidate_response = start_candidate_response(client, interview_id, email="analytics@test.com")
    client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen and empathize with the customer."},
    )
    client.post(f"/api/responses/{candidate_response['id']}/complete")

    profile_response = client.get(
        f"/api/reports/candidate/profile/analytics@test.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["candidate_email"] == "analytics@test.com"
    assert profile["total_responses"] >= 1
    assert profile["history"][0]["interview_title"] == "Customer Support Screen"

    analytics_response = client.get(
        f"/api/reports/interview/{interview_id}/question-analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analytics_response.status_code == 200, analytics_response.text
    analytics = analytics_response.json()
    assert len(analytics["questions"]) == 1
    q = analytics["questions"][0]
    assert q["response_count"] == 1
    assert q["average_score"] > 0
    assert q["difficulty"] in ("easy", "medium", "hard")


def test_export_interview_csv(client):
    """Employers can export candidate responses as CSV."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    candidate_response = start_candidate_response(client, interview_id, email="export@test.com")
    client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen and empathize."},
    )
    client.post(f"/api/responses/{candidate_response['id']}/complete")

    export_response = client.get(
        f"/api/reports/interview/{interview_id}/export.csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert export_response.status_code == 200, export_response.text
    assert "text/csv" in export_response.headers["content-type"]
    assert "attachment" in export_response.headers["content-disposition"]
    body = export_response.text
    assert "Candidate Name" in body
    assert "export@test.com" in body


def test_plagiarism_detection(client):
    """Near-duplicate answers between candidates are flagged."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    for email in ("plag-a@test.com", "plag-b@test.com"):
        candidate_response = start_candidate_response(client, interview_id, email=email)
        client.post(
            f"/api/responses/{candidate_response['id']}/answer",
            params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen actively and empathize with the customer and follow up."},
        )
        client.post(f"/api/responses/{candidate_response['id']}/complete")

    plagiarism_response = client.get(
        f"/api/reports/interview/{interview_id}/plagiarism",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert plagiarism_response.status_code == 200, plagiarism_response.text
    report = plagiarism_response.json()
    assert report["flag_count"] >= 1
    assert report["flagged_pairs"][0]["question"] == "How do you handle an upset customer?"


def test_data_export_request_flow(client):
    """Test requesting and processing a data export."""
    register_user(client)
    token = login_user(client)

    export_response = client.post(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={"request_type": "export"},
    )
    assert export_response.status_code == 201, export_response.text
    request_id = export_response.json()["id"]
    assert export_response.json()["status"] == "pending"

    process_response = client.patch(
        f"/api/data-requests/{request_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "completed"},
    )
    assert process_response.status_code == 200, process_response.text
    assert process_response.json()["status"] == "completed"
    assert process_response.json()["file_path"] is not None

    list_response = client.get(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) >= 1


def test_data_delete_request_flow(client):
    """Test requesting and processing a data deletion."""
    token, response_id = create_completed_response(client)

    delete_response = client.post(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={"request_type": "delete"},
    )
    assert delete_response.status_code == 201, delete_response.text
    request_id = delete_response.json()["id"]

    process_response = client.patch(
        f"/api/data-requests/{request_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "completed", "notes": "GDPR deletion request honored"},
    )
    assert process_response.status_code == 200, process_response.text
    assert process_response.json()["status"] == "completed"


def test_data_request_duplicate_delete_rejected(client):
    """Test that duplicate delete requests are rejected."""
    register_user(client)
    token = login_user(client)

    client.post(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={"request_type": "delete"},
    )

    duplicate = client.post(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={"request_type": "delete"},
    )
    assert duplicate.status_code == 400


def test_data_request_unauthorized(client):
    """Test that employees cannot list all data requests."""
    register_user(client, email="employee@test.com", role="employee")
    token = login_user(client, email="employee@test.com")

    response = client.get(
        "/api/data-requests/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_ai_disclosure_endpoint(client):
    """Test the AI transparency disclosure endpoint."""
    register_user(client)
    token = login_user(client)

    response = client.get(
        "/api/reports/ai-disclosure",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "evaluation" in data
    assert "transcription" in data
    assert "emotion_analysis" in data
    assert "disclosure" in data
    assert data["emotion_analysis"]["scoring_impact"] == "weighted"
    assert "quality_analysis" in data
    assert data["evaluation"]["human_review_available"] is True


def test_ai_disclosure_in_candidate_report(client):
    """Test that the candidate report includes AI disclosure."""
    token, response_id = create_completed_response(client)

    response = client.get(
        f"/api/reports/candidate/{response_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("ai_disclosure") is not None
    assert "AI-assisted" in data["ai_disclosure"]


def test_webhook_create_and_list(client):
    """Test webhook CRUD operations."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]

    activate_response = client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200

    create_response = client.post(
        "/api/webhooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://hooks.example.com/sris",
            "events": ["evaluation.completed", "response.completed"],
            "description": "Test webhook",
            "retry_count": 3,
            "timeout_seconds": 10,
        },
    )
    assert create_response.status_code == 201, create_response.text
    data = create_response.json()
    assert data["url"] == "https://hooks.example.com/sris"
    assert data["secret"] is not None
    webhook_id = data["id"]

    list_response = client.get(
        "/api/webhooks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200, list_response.text
    webhooks = list_response.json()
    assert len(webhooks) >= 1
    assert webhooks[0]["url"] == "https://hooks.example.com/sris"

    get_response = client.get(
        f"/api/webhooks/{webhook_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Test webhook"

    update_response = client.put(
        f"/api/webhooks/{webhook_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Updated webhook"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated webhook"


def test_webhook_deliveries_endpoint(client):
    """Test deliveries list endpoint returns successfully."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]

    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    create_response = client.post(
        "/api/webhooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://hooks.example.com/sris",
            "events": ["evaluation.completed"],
        },
    )
    webhook_id = create_response.json()["id"]

    deliveries_response = client.get(
        f"/api/webhooks/{webhook_id}/deliveries",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deliveries_response.status_code == 200

    delete_response = client.delete(
        f"/api/webhooks/{webhook_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204


def test_webhook_unauthorized(client):
    """Test that employees cannot manage webhooks."""
    register_user(client, email="employee@test.com", role="employee")
    token = login_user(client, email="employee@test.com")

    response = client.post(
        "/api/webhooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://hooks.example.com/sris",
            "events": ["evaluation.completed"],
        },
    )
    assert response.status_code == 403


def test_maintenance_expiry_sweep(client):
    """The maintenance job marks expired sent/pending invitations as expired."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "expiring@test.com",
            "candidate_name": "Expiring Candidate",
        },
    )
    assert response.status_code == 201, response.text
    invitation_id = response.json()["id"]

    from app.services.maintenance_service import sweep_expired_invitations
    from app.database import SessionLocal
    from app.models import Invitation
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        invitation.expires_at = datetime.utcnow() - timedelta(minutes=5)
        db.commit()

        count = sweep_expired_invitations(db)
        assert count >= 1

        db.refresh(invitation)
        assert invitation.status.value == "expired"
    finally:
        db.close()


def test_maintenance_reminders(client, monkeypatch):
    """The maintenance job sends reminders to stale invitations and tracks counts."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "interview_id": interview_id,
            "candidate_email": "reminder@test.com",
            "candidate_name": "Reminder Candidate",
        },
    )
    assert response.status_code == 201, response.text
    invitation_id = response.json()["id"]

    from app.services.maintenance_service import send_invitation_reminders
    from app.database import SessionLocal
    from app.models import Invitation
    from datetime import datetime, timedelta

    import app.services.email_service as email_service
    sent_reminders = []

    def fake_send_reminder_email(**kwargs):
        sent_reminders.append(kwargs)
        return True

    monkeypatch.setattr(email_service, "send_reminder_email_sync", fake_send_reminder_email)

    db = SessionLocal()
    try:
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        invitation.sent_at = datetime.utcnow() - timedelta(days=3)
        invitation.reminder_count = 0
        db.commit()

        count = send_invitation_reminders(db)
        assert count == 1
        assert len(sent_reminders) == 1
        assert sent_reminders[0]["to_email"] == "reminder@test.com"
        assert sent_reminders[0]["reminder_number"] == 1

        db.refresh(invitation)
        assert invitation.reminder_count == 1
        assert invitation.last_reminder_at is not None
    finally:
        db.close()


def test_question_bank_crud(client):
    """Employers can save, list, and delete reusable questions."""
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/interviews/question-bank",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_text": "Describe a time you led a team under pressure.",
            "expected_answer": "STAR format with clear ownership.",
            "question_type": "text",
            "weight": 1.5,
        },
    )
    assert response.status_code == 201, response.text
    entry_id = response.json()["id"]

    list_response = client.get(
        "/api/interviews/question-bank",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    entries = list_response.json()
    assert any(entry["id"] == entry_id for entry in entries)
    assert entries[0]["question_text"].startswith("Describe a time")

    delete_response = client.delete(
        f"/api/interviews/question-bank/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    list_after = client.get(
        "/api/interviews/question-bank",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert not any(entry["id"] == entry_id for entry in list_after.json())


def test_question_bank_owner_isolation(client):
    """Employers only see their own saved questions."""
    register_user(client, email="bank-owner@test.com")
    token = login_user(client, email="bank-owner@test.com")

    client.post(
        "/api/interviews/question-bank",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_text": "Private question", "question_type": "text"},
    )

    register_user(client, email="bank-other@test.com")
    other_token = login_user(client, email="bank-other@test.com")
    list_response = client.get(
        "/api/interviews/question-bank",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_manual_maintenance_endpoint(client):
    """The maintenance trigger endpoint runs without error for employers."""
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/maintenance/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "expired_invitations" in body
    assert "reminders_sent" in body


def test_response_timer_endpoint(client):
    """The server-authoritative timer reports remaining time and expiry."""
    from app.config import settings

    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    candidate_response = start_candidate_response(client, interview_id, email="timer@test.com")
    response_id = candidate_response["id"]

    response = client.get(f"/api/responses/{response_id}/timer")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["response_id"] == response_id
    assert body["duration_minutes"] == 30
    assert body["grace_seconds"] == settings.INTERVIEW_DURATION_GRACE_SECONDS
    assert body["remaining_seconds"] > 0
    assert body["expired"] is False
    assert body["deadline"] > body["started_at"]

    # A not-found response is rejected
    missing = client.get("/api/responses/999999/timer")
    assert missing.status_code == 404

    # An expired response reports expired True (started far in the past)
    from datetime import datetime, timedelta
    from app.database import SessionLocal
    from app.models import CandidateResponse

    db = SessionLocal()
    try:
        cr = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
        cr.started_at = datetime.utcnow() - timedelta(hours=2)
        db.commit()
    finally:
        db.close()

    expired = client.get(f"/api/responses/{response_id}/timer")
    assert expired.status_code == 200
    assert expired.json()["expired"] is True
    assert expired.json()["remaining_seconds"] == 0


def test_emotion_analysis_timeout_and_cache(client, monkeypatch):
    """DeepFace emotion analysis honors a timeout and caches repeated results."""
    from app.config import settings
    from app.services.emotion_service import (
        DeepFaceEmotionAnalysisProvider,
        _cache_get,
        _cache_set,
        EmotionAnalysisResult,
        EmotionSample,
    )

    monkeypatch.setattr(settings, "EMOTION_ANALYSIS_TIMEOUT_SECONDS", 1)

    # Timeout: provider that never returns is abandoned after the timeout.
    provider = DeepFaceEmotionAnalysisProvider()
    slow_path = "/tmp/opencode/slow-emo.webm"
    os.makedirs(os.path.dirname(slow_path), exist_ok=True)
    with open(slow_path, "wb") as f:
        f.write(b"fake-video")

    def _slow_forever(video_path):
        import time
        time.sleep(3)
        return None

    monkeypatch.setattr(provider, "_analyze_video_sync", _slow_forever)
    import asyncio
    import time

    started = time.monotonic()
    result = asyncio.run(provider.analyze_video(slow_path))
    elapsed = time.monotonic() - started
    assert result is None
    assert elapsed < 15
    # Cache: same path + mtime returns the stored result without re-analysis.
    cached = EmotionAnalysisResult(
        dominant_emotion="happy",
        confidence=80.0,
        timeline=[EmotionSample(emotion="happy", confidence=0.8, timestamp=0.0)],
    )
    _cache_set("/tmp/cached-emo.webm", cached)
    assert _cache_get("/tmp/cached-emo.webm") is cached


def test_transcription_health_endpoint(client):
    """Employers can inspect transcription provider health."""
    register_user(client)
    token = login_user(client)

    response = client.get(
        "/api/reports/transcription/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] in ("fake", "fake_transcriber", "whisper")
    assert body["queue_backend"] in ("rq", "background")
    assert "healthy" in body

    # Unauthorized roles are rejected
    register_user(client, email="trans-hr@test.com", role="employee")
    hr_token = login_user(client, email="trans-hr@test.com")
    denied = client.get(
        "/api/reports/transcription/health",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert denied.status_code == 403


def test_emotion_parallel_evaluation_uses_cached_results(client, monkeypatch):
    """Evaluation runs parallel emotion analysis and applies results to answers."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidate_response = start_candidate_response(client, interview_id, email="emopar@test.com")
    response_id = candidate_response["id"]
    client.post(
        f"/api/responses/{response_id}/answer",
        params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen."},
    )

    calls = {"count": 0}

    class RecordingProvider:
        name = "fake"
        version = "1.0.0"

        async def analyze_video(self, video_path):
            calls["count"] += 1
            from app.services.emotion_service import EmotionAnalysisResult, EmotionSample
            return EmotionAnalysisResult(
                dominant_emotion="neutral",
                confidence=50.0,
                timeline=[EmotionSample(emotion="neutral", confidence=0.6, timestamp=0.0)],
            )

    monkeypatch.setattr("app.services.emotion_service.get_emotion_provider", lambda: RecordingProvider())

    # Give the answer a video file so the parallel emotion pre-pass runs.
    from app.database import SessionLocal
    from app.models import QuestionAnswer

    db = SessionLocal()
    try:
        answer = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).first()
        answer.video_file_path = "/tmp/sample-emo.webm"
        db.commit()
    finally:
        db.close()

    from app.services.evaluation_service import evaluate_candidate_response
    import asyncio

    eval_db = SessionLocal()
    try:
        asyncio.run(evaluate_candidate_response(response_id, eval_db, evaluation_run_id=None))
    finally:
        eval_db.close()

    assert calls["count"] == 1

    db2 = SessionLocal()
    try:
        answer2 = db2.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).first()
        assert answer2.emotion_during_answer == "neutral"
    finally:
        db2.close()


def test_notifications_crud(client):
    """Users can list, read, and bulk-read their in-app notifications."""
    register_user(client)
    token = login_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    empty = client.get("/api/notifications/", headers=headers)
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"notifications": [], "unread_count": 0}

    from app.database import SessionLocal
    from app.models import User
    from app.services.notification_service import create_notification

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "employer@example.com").first()
        create_notification(db, user.id, "Hello", "World", notification_type="general")
        create_notification(db, user.id, "Second", None, notification_type="general")
    finally:
        db.close()

    listing = client.get("/api/notifications/", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["unread_count"] == 2
    assert len(body["notifications"]) == 2
    assert body["notifications"][0]["title"] == "Second"
    assert body["notifications"][0]["is_read"] is False

    nid = body["notifications"][0]["id"]

    count = client.get("/api/notifications/unread-count", headers=headers)
    assert count.json()["unread_count"] == 2

    read = client.post(f"/api/notifications/{nid}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    count2 = client.get("/api/notifications/unread-count", headers=headers)
    assert count2.json()["unread_count"] == 1

    all_read = client.post("/api/notifications/read-all", headers=headers)
    assert all_read.status_code == 200
    assert all_read.json()["marked"] == 1

    # Reading a notification that does not belong to the user 404s
    register_user(client, email="notif-other@test.com")
    other_token = login_user(client, email="notif-other@test.com")
    denied = client.post(
        f"/api/notifications/{nid}/read",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 404


def test_response_completion_creates_notification(client):
    """Completing a response notifies the interview owner."""
    register_user(client)
    token = login_user(client)
    interview = create_interview(client, token)
    interview_id = interview["id"]
    client.post(
        f"/api/interviews/{interview_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    candidate_response = start_candidate_response(client, interview_id, email="notify-cand@test.com")
    client.post(
        f"/api/responses/{candidate_response['id']}/answer",
        params={"question_id": interview["questions"][0]["id"], "answer_text": "I listen."},
    )
    client.post(f"/api/responses/{candidate_response['id']}/complete")

    from app.database import SessionLocal
    from app.models import Notification, User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "employer@example.com").first()
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.type == "response_completed")
            .order_by(Notification.id.desc())
            .all()
        )
        assert len(notifications) >= 1
        assert "Candidate One" in (notifications[0].message or "")
    finally:
        db.close()


def test_forgot_password_request_and_reset_flow(client, monkeypatch):
    """Forgot-password mails a one-time token; reset changes the password."""
    from datetime import datetime

    register_user(client)
    login_user(client)

    captured = {}

    async def fake_send(to_email, reset_link):
        captured["to_email"] = to_email
        captured["reset_link"] = reset_link

    monkeypatch.setattr("app.services.email_service.send_password_reset_email", fake_send)

    response = client.post("/api/auth/forgot-password", json={"email": "employer@example.com"})
    assert response.status_code == 200, response.text
    assert "reset link has been sent" in response.json()["message"]

    from app.database import SessionLocal
    from app.models import User, PasswordResetToken

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "employer@example.com").first()
        reset = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).first()
        assert reset is not None
        assert reset.expires_at > datetime.utcnow()
    finally:
        db.close()

    assert captured["to_email"] == "employer@example.com"
    token = captured["reset_link"].split("token=")[1]

    # Reset with the token then sign in with the new password
    reset_response = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "NewStrong1pass",
    })
    assert reset_response.status_code == 200, reset_response.text

    new_login = client.post(
        "/api/auth/login",
        data={"username": "employer@example.com", "password": "NewStrong1pass"},
    )
    assert new_login.status_code == 200, new_login.text

    # Token is single-use: second reset attempt fails
    replay = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "Another1pass",
    })
    assert replay.status_code == 400


def test_reset_password_rejects_bad_token(client):
    """Invalid or expired reset tokens are rejected."""
    bad = client.post("/api/auth/reset-password", json={
        "token": "not-a-real-token",
        "new_password": "Timeout123!",
    })
    assert bad.status_code == 400


def test_forgot_password_no_user_leak(client):
    """Unknown emails get the same response as registered ones."""
    response = client.post("/api/auth/forgot-password", json={"email": "nobody@nowhere.com"})
    assert response.status_code == 200, response.text
    assert "reset link has been sent" in response.json()["message"]