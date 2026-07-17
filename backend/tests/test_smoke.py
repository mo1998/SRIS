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


def login_user(client, email="employer@example.com"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "strong-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_register_and_login_employer(client):
    user = register_user(client)
    token = login_user(client)

    assert user["email"] == "employer@example.com"
    assert token


def test_employer_can_create_interview(client):
    register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/interviews/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Customer Support Screen",
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
    body = response.json()
    assert body["title"] == "Customer Support Screen"
    assert body["status"] == "draft"
    assert len(body["questions"]) == 1