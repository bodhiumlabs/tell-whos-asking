from context.context_classifier import classify_batch


def test_rubric_cases():
    qs = [
        "how do you reset your password",            # 2nd person -> conversational-fragment
        "so, what happens next",                     # discourse marker + comma -> conversational-fragment
        "is this covered under warranty",            # dangling 'this' -> context-dependent
        "does it work offline",                      # 'it' subj, no prior noun -> context-dependent
        "which of the following applies",            # 'the following' -> context-dependent
        "what is the capital of france",             # self-contained
        "how long does photosynthesis take",         # self-contained
    ]
    got = classify_batch(qs)
    assert got == ["conversational-fragment", "conversational-fragment", "context-dependent",
                   "context-dependent", "context-dependent", "self-contained", "self-contained"], got


def test_demonstrative_with_head_noun_is_self_contained():
    # 'this'/'that' as determiner of a head noun is not dangling
    got = classify_batch(["is this book available", "what does that error mean"])
    assert got == ["self-contained", "self-contained"], got
