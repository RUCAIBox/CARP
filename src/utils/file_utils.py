import json


def load_jsonl(load_path):
    samples = []
    with open(load_path, "r", encoding="utf-8") as f:
        for s in map(json.loads, f):
            samples.append(s)
    return samples


def load_jsonl_ml(load_path):
    samples = []
    with open(load_path, "r", encoding="utf-8") as f:
        sample_str = ""
        for line in f:
            sample_str += line
            if line.startswith("}"):
                samples.append(json.loads(sample_str))
                sample_str = ""
    return samples


def save_jsonl(save_path, samples, indent=None):
    with open(save_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False, indent=indent) + "\n")
