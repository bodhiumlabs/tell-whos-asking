from form.pos_adapter import analyze
from form.form_classifier import classify_person

CASES = [
    ("How do I reset my password?", "first"),
    ("We need a refund, who do we contact?", "first"),
    ("What is your return policy?", "second"),
    ("How to reset a password?", "impersonal"),
    ("What does one do here?", "impersonal"),
]


def test_person():
    for q, e in CASES:
        assert classify_person(analyze(q)) == e, f"{q!r} -> expected {e}"
