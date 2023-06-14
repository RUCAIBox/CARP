import json
from tqdm import tqdm
import argparse

from src.utils.file_utils import load_jsonl, load_jsonl_ml
from src.utils.utils import extract_cot_answer, extract_ao_answer
from src.utils.graph_utils import (
    extract_exprs_cot,
    extract_exprs_ao,
    cal_sample_expracc,
)


def evaluate_expracc(data_path):
    original_samples = load_jsonl("data/carp/test.json")
    samples = load_jsonl_ml(data_path)
    save_path = data_path.replace(".json", ".conv.json")
    metrics = {
        "Accuracy": 0,
        "ExprAcc": 0,
        "Fail@first": 0,
        "Fail@middle": 0,
        "Fail@last": 0,
    }
    with open(save_path, "w") as f:
        for s, os in tqdm(zip(samples, original_samples)):
            assert s["answer"] == os["answer"]
            if len(s["generation"][0]) > 0 and isinstance(
                s["generation"][0][0], str
            ):  # CoT
                generation = s["generation"][0][0]
                extract_exprs_fn = extract_exprs_cot
                generated_ans = extract_cot_answer(generation, "答案是：")
            else:  # ReAct
                generation = (
                    s["generation"][-1]
                    if len(s["generation"]) > 1
                    else s["generation"][0]
                )
                extract_exprs_fn = extract_exprs_ao
                generated_ans = extract_ao_answer(generation)
            expracc, recalls = cal_sample_expracc(
                generation,
                generated_ans,
                os["answer"],
                os["exprs"],
                os["edges"],
                extract_exprs_fn,
            )
            metrics["ExprAcc"] += expracc
            if expracc == 0.0:
                metrics["Fail@first"] += 1
            elif len(os["exprs"]) == expracc * len(os["exprs"]) + 1:
                metrics["Fail@last"] += 1
            elif expracc != 1.0:
                metrics["Fail@middle"] += 1
            else:
                metrics["Accuracy"] += 1
            s["expracc"] = expracc
            f.write(json.dumps(s, indent=4, ensure_ascii=False) + "\n")
            f.flush()

    for key in ["Fail@first", "Fail@middle", "Fail@last"]:
        metrics[key] /= len(samples) - metrics["Accuracy"]
    for key in ["Accuracy", "ExprAcc"]:
        metrics[key] /= len(samples)

    for key in metrics:
        print(f"{key}: {metrics[key]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_path", type=str, default=None)
    args = parser.parse_args()
    evaluate_expracc(args.result_path)
