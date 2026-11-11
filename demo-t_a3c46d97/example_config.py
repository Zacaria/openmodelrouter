"""Print a configuration for synthetic-only offline demonstration."""
import json
import sys

command = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"answer":"simulated response","usage":{},"provenance":"simulated"}))']
decider = [sys.executable, '-c', 'import json,sys; json.load(sys.stdin); print(json.dumps({"route":"low"}))']
route = {'model':'synthetic-default', 'effort':'none', 'command':command}
print(json.dumps({'default_route':'low', 'decision_command':decider, 'timeout_seconds':10,
                  'routes':{'low':route, 'high':route}}))
