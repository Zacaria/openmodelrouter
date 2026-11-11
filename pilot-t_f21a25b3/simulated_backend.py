import json
import sys

# Offline protocol fixture, not model inference or a routing baseline.
json.load(sys.stdin)
print(json.dumps({'answer': 'ok', 'usage': {'input': 10, 'output': 2}, 'rates': {'input': 2, 'output': 4}, 'decision_cost': 0, 'retry_cost': 0}))
