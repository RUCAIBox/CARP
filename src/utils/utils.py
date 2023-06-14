import re
import time
import os
import json
import random
import string
from enum import Enum, auto
from tqdm import tqdm
from collections import OrderedDict
import dataclasses
import ast
import timeout_decorator
import tiktoken
import networkx as nx
import sympy as sp
from sympy.parsing.latex import parse_latex

from src.prompt_pattern import FewShotPattern


def remove_space_in_chinese(text):
    return re.sub(r"(?<=[\u4e00-\u9fff]) +(?=[\u4e00-\u9fff])", "", text)


def find_first_capital_letter(answer):
    letter_set = {"A", "B", "C", "D", "E", "F"}
    for c in answer:
        if c in letter_set:
            return c
    return ""


def num_tokens_from_string(string: str, encoding_name: str = "p50k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print(
            "Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print(
            "Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314."
        )
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def find_answer_math(s):
    ans = s.split("boxed")
    if len(ans) == 1:
        return ""
    ans = ans[-1]
    if len(ans) == 0:
        return ""
    try:
        if ans[0] == "{":
            stack = 1
            a = ""
            for c in ans[1:]:
                if c == "{":
                    stack += 1
                    a += c
                elif c == "}":
                    stack -= 1
                    if stack == 0:
                        break
                    a += c
                else:
                    a += c
        else:
            a = ans.split("$")[0].strip()
    except:
        return ""
    return a


def extract_last_action(text, output_prefix="Output:"):
    last_line = text.strip().split(output_prefix)[-1].strip()
    last_line = last_line.strip("。").strip(".")
    if "[" in last_line:
        try:
            output_list = eval(last_line)
            if isinstance(output_list, list) and len(output_list) == 1:
                return output_list[0]
        except:
            return last_line
    return last_line


def extract_ao_answer(text, answer_prefix="Final Answer: "):
    if isinstance(text, list):
        text = "\n".join([t["content"] for t in text])
    split_list = text.split(answer_prefix)
    if len(split_list) == 1:
        if "boxed" in text:
            answer = find_answer_math(text)
        else:
            answer = extract_last_action(text)
    else:
        answer = split_list[-1].strip().strip("。.：:")
        if "boxed" in answer:
            answer = find_answer_math(answer)
    return answer


def extract_choice_answer(text, answer_prefix="The answer is: "):
    if isinstance(text, list):
        text = "\n".join([t["content"] for t in text])
    answer = find_first_capital_letter(extract_cot_answer(text, answer_prefix))
    if answer == "":
        matches = re.findall(r"\(([A-F])\)", text)
        if len(matches) == 0:
            return ""
        return matches[-1]
    return answer


def extract_cot_answer(text, answer_prefix="The answer is: "):
    if isinstance(text, list):
        text = "\n".join([t["content"] for t in text])
    split_list = text.split(answer_prefix)
    if len(split_list) == 1:
        answer = find_answer_math(text)
        if answer == "" and answer_prefix == "答案是：" and "答案为" in text:
            return extract_cot_answer(text, answer_prefix="答案为")
        if answer == "" and answer_prefix == "答案是：" and "答案是:" in text:
            return extract_cot_answer(text, answer_prefix="答案是:")
    else:
        answer = split_list[-1].strip().strip("。.：:")
    return answer


def get_demos(
    args,
    demo_samples,
    prompt_pattern: FewShotPattern,
    do_reverse=False,
    do_drop_long=False,
):
    prefix = prompt_pattern.final_prefix
    suffix = prompt_pattern.final_suffix
    demos = ""
    temp_demos = ""
    for i, sample in enumerate(demo_samples):
        question = sample[args.input_col]
        steps = sample[args.step_col]
        if args.output_col in sample:
            answer = sample[args.output_col]
        else:
            answer = extract_cot_answer(sample[args.step_col])
        input_pattern = prompt_pattern.combined_inputs_w_target_prefix
        target_pattern = prompt_pattern.combined_targets_wo_target_prefix
        input_text = input_pattern.format(question=question)
        target_text = target_pattern.format(chain_of_thought=steps, answer=answer)
        demo = input_text + target_text
        if do_reverse:
            temp_demos = demo + temp_demos
        else:
            temp_demos += demo
        if do_drop_long:
            num_tokens = num_tokens_from_string(prefix + temp_demos + suffix)
            if num_tokens + args.max_tokens >= 4090:
                print("[Warning] skip examplars")
                break
        demos = temp_demos
    demos = prefix + demos + suffix
    return demos


def create_message(role, message):
    return {"role": role, "content": message}
