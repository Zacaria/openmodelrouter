"""Conservative evaluator: unsupported oracles are never counted as success."""

def evaluate(case, answers):
    if case['family'] not in ('simple', 'conversation'):
        return 'not_evaluated'
    expected = case['expected']
    if len(answers) != len(expected):
        return 'fail'
    return 'pass' if all(isinstance(a, str) and a.strip() == e for a, e in zip(answers, expected)) else 'fail'
