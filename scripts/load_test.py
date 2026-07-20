#!/usr/bin/env python3
"""Small HTTP load harness for SRIS release smoke testing.

This script intentionally uses only the Python standard library so it can run
from an operator workstation without installing extra packages.
"""

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.parse
import urllib.request


def request(base_url, method, path, token=None, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Request-ID": f"load-{time.time_ns()}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        data=body,
        headers=headers,
        method=method,
    )
    started_at = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as response:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response_body = response.read().decode("utf-8")
        return response.status, json.loads(response_body) if response_body else {}, elapsed_ms


def register_and_login(base_url, run_id):
    email = f"load-employer-{run_id}@example.com"
    request(base_url, "POST", "/api/auth/register", payload={
        "email": email,
        "password": "strong-password",
        "full_name": "Load Employer",
        "role": "employer",
        "company_name": "SRIS Load Test",
    })

    form = urllib.parse.urlencode({"username": email, "password": "strong-password"}).encode("utf-8")
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url.rstrip("/") + "/", "/api/auth/login".lstrip("/")),
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def create_interview(base_url, token, run_id):
    _, interview, _ = request(base_url, "POST", "/api/interviews/", token=token, payload={
        "title": f"Load Test Interview {run_id}",
        "description": "Release smoke load test",
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
                    {"name": "Ownership", "description": "Takes ownership", "weight": 1, "order_index": 0}
                ],
            }
        ],
    })
    request(base_url, "POST", f"/api/interviews/{interview['id']}/activate", token=token)
    return interview


def candidate_flow(base_url, interview, candidate_index):
    _, response, start_ms = request(base_url, "POST", "/api/responses/", payload={
        "interview_id": interview["id"],
        "candidate_email": f"load-candidate-{candidate_index}-{time.time_ns()}@example.com",
        "candidate_name": f"Load Candidate {candidate_index}",
    })
    _, _, answer_ms = request(
        base_url,
        "POST",
        f"/api/responses/{response['id']}/answer?" + urllib.parse.urlencode({
            "question_id": interview["questions"][0]["id"],
            "answer_text": "I listen, empathize, clarify, take ownership, resolve, and follow up.",
            "time_taken_seconds": 90,
        }),
    )
    _, _, complete_ms = request(base_url, "POST", f"/api/responses/{response['id']}/complete")
    return {"start_ms": start_ms, "answer_ms": answer_ms, "complete_ms": complete_ms}


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percent / 100) * (len(ordered) - 1)))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser(description="Run SRIS HTTP load smoke flow")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--candidates", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()

    run_id = int(time.time())
    token = register_and_login(args.base_url, run_id)
    interview = create_interview(args.base_url, token, run_id)

    started_at = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda index: candidate_flow(args.base_url, interview, index), range(args.candidates)))
    total_seconds = time.perf_counter() - started_at

    complete_latencies = [result["complete_ms"] for result in results]
    print(json.dumps({
        "candidates": args.candidates,
        "concurrency": args.concurrency,
        "total_seconds": round(total_seconds, 2),
        "complete_avg_ms": round(statistics.mean(complete_latencies), 2),
        "complete_p95_ms": round(percentile(complete_latencies, 95), 2),
    }, indent=2))


if __name__ == "__main__":
    main()