def register_user(client, email="employer@example.com", role="employer"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "strong-password",
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
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_tokens(client, email="employer@example.com"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "strong-password"},
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
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_and_login_employer(client):
    user = register_user(client)
    token = login_user(client)

    assert user["email"] == "employer@example.com"
    assert token


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
        json={"current_password": "strong-password", "new_password": "new-strong-password"},
    )
    assert response.status_code == 204, response.text

    old_login_response = client.post(
        "/api/auth/login",
        data={"username": "employer@example.com", "password": "strong-password"},
    )
    assert old_login_response.status_code == 401, old_login_response.text

    new_login_response = client.post(
        "/api/auth/login",
        data={"username": "employer@example.com", "password": "new-strong-password"},
    )
    assert new_login_response.status_code == 200, new_login_response.text


def test_current_user_password_change_rejects_wrong_current_password(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong-password", "new_password": "new-strong-password"},
    )

    assert response.status_code == 400, response.text


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