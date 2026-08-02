from form.form_classifier import classify


def test_classify_shape():
    r = classify("How do I reset my password?")
    assert r == {"type": "wh", "person": "first", "n_tokens": 6,
                 "length_bucket": "short", "has_scaffolding": False}


def test_classify_empty():
    r = classify("")
    assert r["type"] == "other" and r["person"] == "impersonal"
