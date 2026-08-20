import pytest

from app.services.pii_masking import EMAIL_TOKEN, NAME_TOKEN, PHONE_TOKEN, mask_pii


def test_mask_pii_redacts_email_phone_and_name():
    text = "My email is john.smith@example.com, call me at +1 (555) 123-4567, I am John Smith."
    masked, summary = mask_pii(text, candidate_name="John Smith")

    assert EMAIL_TOKEN in masked
    assert "john.smith@example.com" not in masked
    assert PHONE_TOKEN in masked
    assert "555" not in masked
    assert NAME_TOKEN in masked
    assert "John Smith" not in masked
    assert summary.masked is True
    assert summary.emails == 1
    assert summary.phones == 1
    assert summary.names >= 1


def test_mask_pii_leaves_clean_arabic_text_untouched():
    text = "أفضل طريقة هي الاستماع ثم المتابعة مع العميل"
    masked, summary = mask_pii(text, candidate_name=None)

    assert masked == text
    assert summary.masked is False
    assert summary.emails == 0
    assert summary.phones == 0
    assert summary.names == 0


def test_mask_pii_handles_arabic_indic_phone_digits():
    text = "اتصل بي على ٠١٢٣٤٥٦٧٨٩"
    masked, summary = mask_pii(text, candidate_name=None)

    assert PHONE_TOKEN in masked
    assert summary.phones >= 1


def test_mask_pii_no_candidate_name_skips_name_redaction():
    text = "I am John Smith and my email is j@example.com"
    masked, summary = mask_pii(text, candidate_name=None)

    assert "John Smith" in masked
    assert EMAIL_TOKEN in masked
    assert summary.names == 0


def test_mask_pii_ignores_short_or_numeric_name_tokens():
    text = "My name is Al and I have 5000 in account."
    masked, summary = mask_pii(text, candidate_name="Al")

    assert "Al" in masked
    assert summary.names == 0