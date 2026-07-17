from app.database import SessionLocal
from app.models import TeamMembership, TeamRole, User


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


def test_employer_can_create_interview(client):
    register_user(client)
    token = login_user(client)

    body = create_interview(client, token)
    assert body["title"] == "Customer Support Screen"
    assert body["status"] == "draft"
    assert body["organization_id"] is not None
    assert len(body["questions"]) == 1


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
    owner_org_response = client.get(
        "/api/users/me/organization",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_org_response.status_code == 200, owner_org_response.text
    owner_org = owner_org_response.json()
    interview = create_interview(client, owner_token)

    register_user(client, email="reviewer@example.com")
    reviewer_token = login_user(client, email="reviewer@example.com")
    reviewer = current_user(client, reviewer_token)

    db = SessionLocal()
    try:
        reviewer_user = db.query(User).filter(User.id == reviewer["id"]).first()
        db.add(TeamMembership(
            organization_id=owner_org["id"],
            user_id=reviewer_user.id,
            role=TeamRole.REVIEWER,
        ))
        db.commit()
    finally:
        db.close()

    response = client.get(
        f"/api/interviews/{interview['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == interview["id"]