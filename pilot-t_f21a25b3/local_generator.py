"""Tiny offline CPU generator for synthetic testing, not an agent backend."""
import json
import os
import sys

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    weights = sys.argv[1]
    request = json.load(sys.stdin)
    messages = request['messages']
    if not messages or any(set(m) != {'role', 'content'} or m['role'] not in ('system', 'user', 'assistant') or not isinstance(m['content'], str) for m in messages):
        raise ValueError('invalid messages')
    prompt = '\n'.join(m['role'] + ': ' + m['content'] for m in messages) + '\nassistant: '
    tokenizer = AutoTokenizer.from_pretrained(weights, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(weights, local_files_only=True)
    inputs = tokenizer(prompt, return_tensors='pt')
    output = model.generate(**inputs, max_new_tokens=8, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    count = inputs.input_ids.shape[1]
    print(json.dumps({'answer':tokenizer.decode(output[0][count:], skip_special_tokens=True),
                      'usage':{'input':count, 'output':output.shape[1]-count},
                      'provenance':'real-local'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
