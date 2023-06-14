import os, sys, inspect

currenddir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currenddir)
sys.path.insert(0, parentdir)
import copy
import json
import argparse
import tqdm
import random

random.seed(42)

from src.core.runtime import ApiRuntime
from src.core.react import ChatReActInterface, ChatIterRewriteRetActionInterface
from src.utils.math_utils import compare_ans
from src.utils.file_utils import load_jsonl_ml


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_name", type=str, default="gpt-3.5-turbo", help="API model name."
    )
    parser.add_argument(
        "--answer_prefix",
        default="答案是：",
        type=str,
        help="The answer prefix for extracting answer.",
    )
    parser.add_argument(
        "--input_col", default="content", type=str, help="Input column name."
    )
    parser.add_argument(
        "--step_col", default="program", type=str, help="Solving process column name."
    )
    parser.add_argument(
        "--output_col", default="answer", type=str, help="Output answer name."
    )
    parser.add_argument(
        "--temperature", default=0.0, type=float, help="Temperature for API."
    )
    parser.add_argument(
        "--data_path",
        default="data/carp/test.json",
        type=str,
        help="Path to test dataset.",
    )
    parser.add_argument(
        "--demo_path",
        default="data/carp/demo.json",
        type=str,
        help="Path to demonstrations",
    )
    parser.add_argument(
        "--output_path", default="eval_results/carp-random_cot.json", type=str, help="Path to result path."
    )
    parser.add_argument(
        "--max_samples", default=None, type=int, help="Max number of test samples"
    )
    parser.add_argument(
        "--append", action="store_true", help="Append after existing results"
    )
    parser.add_argument(
        "--num_skips", type=int, default=0, help="Number of skipping samples"
    )
    parser.add_argument(
        "--num_react_samples", default=1, type=int, help="Number trials of ReAct"
    )
    parser.add_argument(
        "--prompt_path", default=None, type=str, help="Path to the Stage 1 prompt"
    )
    parser.add_argument(
        "--system_msg_path",
        type=str,
        default=None,
        help="Path to the Stage 1 system prompt",
    )
    parser.add_argument(
        "--reflect_prompt_path",
        default=None,
        type=str,
        help="Path to the Stage 2 prompt",
    )
    parser.add_argument(
        "--reflect_system_msg_path",
        type=str,
        default=None,
        help="Path to the Stage 2 system prompt",
    )
    parser.add_argument(
        "--message_schema",
        type=str,
        default=None,
        help="Path to message schema for the Stage 2",
    )
    parser.add_argument(
        "--add_call_feedback", action="store_true", help="Do add call failing feedbcak"
    )
    parser.add_argument(
        "--do_sample_data", action="store_true", help="Do sample samples"
    )
    parser.add_argument("--reflect_type", default=None, type=str, help="None / Iter")
    parser.add_argument("--num_trials", type=int, default=3)
    parser.add_argument(
        "--drop_system", action="store_true", help="Do use user role for system msg"
    )
    parser.add_argument(
        "--do_reverse_role",
        action="store_true",
        help="Do reverse role when calling think",
    )
    parser.add_argument(
        "--do_drop_nl_answer",
        action="store_true",
        help="Do drop CoT answer when deliberating",
    )
    parser.add_argument(
        "--case_spliter", type=str, default=None, help="Symbol to split demonstrations"
    )
    parser.add_argument("--max_tokens", type=int, default=512)
    parser.add_argument("--reflect_max_tokens", type=int, default=512)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    with open(args.prompt_path, "r") as f:
        prompt_pattern = f.read()

    if args.reflect_prompt_path is not None:
        with open(args.reflect_prompt_path, "r") as f:
            reflect_pattern = f.read()
    else:
        reflect_pattern = None

    interface_args = {
        "model": args.model_name,
        "runtime": ApiRuntime(),
        "stop": "\nOutput:",
        "num_react_samples": args.num_react_samples,
        "add_call_feedback": args.add_call_feedback,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reason_prompt_temp": prompt_pattern,
        "reflect_prompt_temp": reflect_pattern,
        "reason_bootstrap": None,
        "reflect_bootstrap": None,
    }

    itf_class = ChatReActInterface
    with open(args.system_msg_path, "r") as f:
        system_msg = f.read()
    interface_args["reason_bootstrap"] = system_msg
    interface_args["drop_system"] = args.drop_system
    interface_args["do_reverse_role"] = args.do_reverse_role
    interface_args["case_spliter"] = args.case_spliter
    if args.reflect_type == None:
        itf_class = ChatReActInterface
    elif args.reflect_type == "iter":
        interface_args["do_drop_nl_answer"] = args.do_drop_nl_answer
        interface_args["nl_answer_prefix"] = args.answer_prefix
        interface_args["reflect_max_tokens"] = args.reflect_max_tokens
        itf_class = ChatIterRewriteRetActionInterface
    with open(args.reflect_system_msg_path, "r") as f:
        reflect_system_msg = f.read()
    interface_args["reflect_bootstrap"] = reflect_system_msg
    interface_args["num_trials"] = args.num_trials
    message_schema = None
    if args.message_schema is not None:
        with open(args.message_schema, "r") as f:
            message_schema = f.read()
    interface_args["message_schema"] = message_schema

    itf = itf_class(**interface_args)

    try:
        examples = list(map(json.loads, open(args.data_path)))
    except:
        examples = load_jsonl_ml(args.data_path)

    if args.max_samples is not None:
        if args.do_sample_data:
            random.shuffle(examples)
        examples = examples[: args.max_samples]

    os.makedirs("eval_results", exist_ok=True)
    scores = []
    old_scores = []
    num_skip_exps = args.num_skips

    with open(args.output_path, "a" if args.append else "w") as f:
        pbar = tqdm.tqdm(
            examples[num_skip_exps:], initial=num_skip_exps, total=len(examples)
        )
        for x in pbar:
            question = x[args.input_col]
            steps = copy.copy(x)
            if "score" in x:
                steps["old_score"] = x["score"]
                old_scores.append(x["score"])
            for key in list(steps.keys()):
                if key not in [
                    "id",
                    args.input_col,
                    args.output_col,
                    args.step_col,
                    "old_score",
                ]:
                    del steps[key]
            old_scratchpad = x["generation"][0][0]
            ans = itf.run(question, old_scratchpad)
            score = 1 if compare_ans(ans, x[args.output_col]) else 0
            scores.append(score)

            steps["generation"] = itf.history
            steps["old_generation"] = (
                old_scratchpad
                if not (
                    args.reflect_type is not None
                    and args.reflect_type.startswith("iter")
                )
                else itf.nl_history
            )
            steps["generated_ans"] = ans
            steps["score"] = score
            f.write(json.dumps(steps, ensure_ascii=False, indent=4) + "\n")

            itf.clear_history()
            f.flush()
    print(f"Accuracy - {sum(scores) / len(scores)}")
