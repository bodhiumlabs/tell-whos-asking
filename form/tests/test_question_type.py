from form.pos_adapter import analyze
from form.form_classifier import classify_type

CASES = [
    ("How do I reset my password?", "wh"),
    ("What is your return policy?", "wh"),
    ("Is Python faster than Go?", "polar"),
    ("Do you ship to Canada?", "polar"),
    ("Tell me how to bake bread.", "imperative-interrogative"),
    ("Explain the difference between TCP and UDP.", "imperative-interrogative"),
    ("best way to lose weight?", "elliptical"),
    ("cheapest flights to New York?", "elliptical"),
    ("You like it, right?", "tag"),
    ("42", "other"),
]


def test_question_type():
    for q, expected in CASES:
        assert classify_type(analyze(q)) == expected, f"{q!r} -> expected {expected}"
