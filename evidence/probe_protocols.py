"""Synthetic protocol qualification; no credentials or host integration claims."""
import json
import argparse
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
BASE = args.base_url.rstrip('/')
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
OUT = args.output
if OUT.exists():
    raise FileExistsError('Choose a new output path; previous evidence is preserved.')
results = []


def post(path, body):
    started = time.monotonic()
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(request, timeout=120) as response:
        if body.get('stream'):
            frames = []
            for line in response:
                if line.strip():
                    frames.append({'ms': round((time.monotonic()-started)*1000, 3), 'line': line.decode().strip()})
            result = {'frames': frames}
        else:
            result = json.load(response)
    results.append({'path': path, 'request': body, 'response': result, 'elapsed_ms': (time.monotonic()-started)*1000, 'provenance': 'real-local-generation'})
    OUT.write_text(json.dumps(results, indent=2))
    return result


schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}
prompt = 'Call read_fixture to find the secret word in this synthetic fixture. Do not guess it. After the tool result, reply only with that word.'
try:
    for protocol in ['chat', 'responses', 'messages']:
        try:
            if protocol == 'chat':
                path = '/v1/chat/completions'
                messages = [{'role': 'user', 'content': prompt}]
                tool = {'type': 'function', 'function': {'name': 'read_fixture', 'description': 'Read synthetic fixture and return its word.', 'parameters': schema}}
                body = {'model': MODEL, 'messages': messages, 'tools': [tool], 'temperature': 0, 'max_tokens': 128, 'reasoning_effort': 'none'}
                first = post(path, body)
                assistant = first['choices'][0]['message']
                call = assistant['tool_calls'][0]
                assert call['function']['name'] == 'read_fixture'
                body['messages'] += [assistant, {'role': 'tool', 'tool_call_id': call['id'], 'content': 'SYNTHETIC-ORCHID'}]
            elif protocol == 'responses':
                path = '/v1/responses'
                tool = {'type': 'function', 'name': 'read_fixture', 'description': 'Read synthetic fixture and return its word.', 'parameters': schema}
                body = {'model': MODEL, 'input': [{'role': 'user', 'content': prompt}], 'tools': [tool], 'max_output_tokens': 128, 'reasoning': {'effort': 'none'}, 'store': False}
                first = post(path, body)
                calls = [x for x in first['output'] if x['type'] == 'function_call']
                assert calls[0]['name'] == 'read_fixture'
                body['input'] += first['output'] + [{'type': 'function_call_output', 'call_id': calls[0]['call_id'], 'output': 'SYNTHETIC-ORCHID'}]
            else:
                path = '/v1/messages'
                tool = {'name': 'read_fixture', 'description': 'Read synthetic fixture and return its word.', 'input_schema': schema}
                body = {'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'tools': [tool], 'max_tokens': 128, 'thinking': {'type': 'disabled'}}
                first = post(path, body)
                calls = [x for x in first['content'] if x['type'] == 'tool_use']
                assert calls[0]['name'] == 'read_fixture'
                body['messages'] += [{'role': 'assistant', 'content': first['content']}, {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': calls[0]['id'], 'content': 'SYNTHETIC-ORCHID'}]}]
            body['stream'] = True
            streamed = post(path, body)
            text = ''
            for frame in streamed['frames']:
                line = frame['line']
                if not line.startswith('data: ') or line == 'data: [DONE]':
                    continue
                event = json.loads(line[6:])
                if protocol == 'chat':
                    text += ''.join(choice.get('delta', {}).get('content', '') or '' for choice in event.get('choices', []))
                elif protocol == 'messages':
                    text += event.get('delta', {}).get('text', '')
                elif event.get('type') == 'response.output_text.delta':
                    text += event['delta']
            assert text == 'SYNTHETIC-ORCHID', repr(text)
            print(protocol, 'tool/result/stream PASS', flush=True)
        except Exception as error:
            results.append({'protocol': protocol, 'error': type(error).__name__, 'provenance': 'real-failure'})
            OUT.write_text(json.dumps(results, indent=2))
            print(protocol, type(error).__name__, flush=True)
finally:
    post('/api/generate', {'model': MODEL, 'keep_alive': 0})
    print('Evidence:', OUT)
