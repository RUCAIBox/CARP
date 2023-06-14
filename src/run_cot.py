# Copyright 2022 PAL Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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

from src.core.cot import TextInterface, ProgramInterface
from src.core.runtime import ApiRuntime
from src.prompt_pattern import COT_PATTERNS
from src.utils.utils import (
    get_demos,
    extract_choice_answer,
)
from src.utils.math_utils import compare_ans
from src.utils.file_utils import load_jsonl, load_jsonl_ml


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface_type", type=str, default="text", help="Type of interface, including text / code.")
    parser.add_argument("--model_name", type=str, default="gpt-3.5-turbo", help="API model name.")
    parser.add_argument("--append", action="store_true", help="Append after existing results")
    parser.add_argument("--answer_prefix", default="答案是：", type=str, help="The answer prefix for extracting answer.")
    parser.add_argument("--input_col", default="content", type=str, help="Input column name.")
    parser.add_argument("--step_col", default="program", type=str, help="Solving process column name.")
    parser.add_argument("--output_col", default="answer", type=str, help="Output answer name.")
    parser.add_argument("--temperature", default=0.0, type=float, help="Temperature for API.")
    parser.add_argument("--data_path", default="data/carp/test.json", type=str, help="Path to test dataset.")
    parser.add_argument("--demo_path", default="data/carp/demo.json", type=str, help="Path to demonstrations")
    parser.add_argument(
        "--output_path", default="eval_results/carp-random_cot.json", type=str, help="Path to result path."
    )
    parser.add_argument("--num_demos", default=8, type=int, help="Max number of demonstrations")
    parser.add_argument("--num_beams", default=1, type=int, help="Number of completions of API")
    parser.add_argument("--do_retrieval", action="store_true", help="Do retrieval-augmented CoT")
    parser.add_argument("--ret_path", default=None, type=str, help="Path to retrieval demonstrations")
    parser.add_argument("--max_samples", default=None, type=int, help="Max number of test samples")
    parser.add_argument("--prompt_type", default="zh", type=str)
    parser.add_argument("--num_skips", type=int, default=0)
    parser.add_argument("--do_sample_data", action="store_true")
    parser.add_argument("--num_trials", type=int, default=3)
    parser.add_argument("--max_tokens", type=int, default=512)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.interface_type == "text":
        prompt_pattern = COT_PATTERNS[args.prompt_type]
        if not args.do_retrieval and args.interface_type == "text":
            demo_samples = load_jsonl(args.demo_path)
        else:
            with open(args.ret_path, "r") as f:
                r_samples = json.load(f)
        interface_cls = TextInterface
        itf = interface_cls(
            model=args.model_name,
            answer_prefix=args.answer_prefix,
            num_beams=args.num_beams,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    elif args.interface_type == "code":
        with open(args.prompt_path, "r") as f:
            prompt_pattern = f.read()
        itf = ProgramInterface(
            model=args.model_name,
            stop=None,
            get_answer_expr="solution()",
            verbose=args.verbose,
            runtime=ApiRuntime() if args.use_code_tool else None,
        )

    try:
        examples = list(map(json.loads, open(args.data_path)))
    except:
        examples = load_jsonl_ml(args.data_path)

    if args.max_samples is not None:
        if args.do_sample_data:
            random.shuffle(examples)
        examples = examples[: args.max_samples]

    os.makedirs("eval_results", exist_ok=True)
    num_skip_exps = args.num_skips
    scores = []

    with open(args.output_path, "a" if args.append else "w") as f:
        pbar = tqdm.tqdm(
            examples[num_skip_exps:], initial=num_skip_exps, total=len(examples)
        )
        for i, x in enumerate(pbar):
            question = x[args.input_col]
            steps = copy.copy(x)
            if args.interface_type == "text":
                if not args.do_retrieval:
                    temp_demo_samples = [
                        s
                        for s in demo_samples
                        if s[args.input_col] != x[args.input_col]
                    ]
                    prompt = get_demos(
                        args,
                        demo_samples=temp_demo_samples,
                        prompt_pattern=prompt_pattern,
                        do_drop_long=True,
                    )
                else:
                    query = [question]
                    demo_samples = r_samples[i + num_skip_exps]
                    demo_samples = demo_samples[: args.num_demos]
                    prompt = get_demos(
                        args,
                        demo_samples,
                        prompt_pattern,
                        do_reverse=True,
                        do_drop_long=True,
                    )
                curr_pattern = prompt_pattern.combined_inputs_w_target_prefix
                curr_sample = curr_pattern.format(question=question)
                prompt += curr_sample
                ans = itf.run(prompt)
            elif args.interface_type == "code":
                prompt = prompt_pattern.replace("{question}", question)
                ans = itf.run(prompt=prompt, num_beams=args.num_beams)
            else:
                prompt = prompt_pattern.replace("{question}", question)
                ans = itf.run(
                    prompt=prompt,
                    num_beams=args.num_beams,
                    temperature=args.temperature,
                )

            if "sat" in args.data_path or "gaokao-mathqa" in args.data_path:
                score = (
                    1
                    if extract_choice_answer(
                        itf.history[0][-1], answer_prefix=itf.answer_prefix
                    )
                    == x[args.output_col]
                    else 0
                )
            elif isinstance(ans, list):
                score = 1 if compare_ans(ans[0], x[args.output_col]) else 0
            else:
                score = 1 if compare_ans(ans, x[args.output_col]) else 0
            scores.append(score)

            for key in list(steps.keys()):
                if key not in ["id", args.input_col, args.output_col, args.step_col]:
                    del steps[key]

            if args.do_retrieval:
                steps["retrieval"] = [
                    s["content"] for s in demo_samples[: args.num_demos]
                ]

            steps["generation"] = itf.history
            steps["generated_ans"] = ans
            steps["score"] = score
            f.write(json.dumps(steps, ensure_ascii=False, indent=4) + "\n")

            itf.clear_history()
            f.flush()

    print(f"Accuracy - {sum(scores) / len(scores)}")
