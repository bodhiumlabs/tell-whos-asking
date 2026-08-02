from form.pos_adapter import analyze
from form.form_classifier import length_and_scaffold


def test_length_bucket():
    assert length_and_scaffold(analyze("How to reset?"))["length_bucket"] == "short"
    assert length_and_scaffold(analyze("How do I reset my account password today?"))["length_bucket"] == "medium"


def test_scaffolding():
    assert length_and_scaffold(analyze("How to reset?"))["has_scaffolding"] is False
    assert length_and_scaffold(analyze("I recently moved. How do I change my address?"))["has_scaffolding"] is True
    assert length_and_scaffold(analyze("Please tell me how to bake bread."))["has_scaffolding"] is True
    assert length_and_scaffold(analyze("Since I moved, how do I update my address?"))["has_scaffolding"] is True
