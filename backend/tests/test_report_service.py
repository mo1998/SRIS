import json

from app.services.report_service import format_evaluation_evidence


def test_format_evaluation_evidence_supports_llm_and_fallback_keys():
    lines = format_evaluation_evidence(json.dumps({
        "matched_criteria": ["clear structure", "specific example"],
        "missing_criteria": ["metric"],
        "evidence": "Candidate gave a clear example.",
    }))

    assert "clear structure" in lines[0]
    assert "specific example" in lines[0]
    assert "metric" in lines[1]
    assert "Candidate gave a clear example." in lines[2]

    fallback_lines = format_evaluation_evidence(json.dumps({
        "matched_keywords": ["listen"],
        "missing_keywords": [],
        "provider_fallback_from": "local_vllm",
    }))

    assert "listen" in fallback_lines[0]
    assert "local_vllm" in fallback_lines[1]