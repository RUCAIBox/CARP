import json

def load_jsonl(load_path):
    samples = []
    with open(load_path, "r", encoding="utf-8") as f:
        for s in map(json.loads, f):
            samples.append(s)
    return samples

for key in ["train", "test", "dev"]:
    print(load_jsonl(f"data/carp_en/{key}.json")[0])