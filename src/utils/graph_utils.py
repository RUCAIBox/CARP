import json
import networkx as nx
import re
import ast
from tqdm import tqdm
import sys

sys.path.append(".")
from src.utils.math_utils import (
    compare_ans,
    my_parse_latex,
    clean_expr_str,
    is_expr_equal,
    my_equals,
)
from collections.abc import Iterable


def flatten_list(x):
    if isinstance(x, Iterable) and not isinstance(x, str):
        return [a for i in x for a in flatten_list(i)]
    else:
        return [x]


def split_chinese(text):
    pattern = re.compile(r"[\u4e00-\u9fff]+")
    return pattern.split(text)


def extract_exprs_ao(text):
    def get_exprs(text):
        def get_text_exprs(subtext):
            if "$" in subtext:
                return extract_exprs_cot(subtext)
            return [subtext]

        exprs = []
        if "[" in text:
            try:
                output_list = eval(text)
                if isinstance(output_list, list):
                    for o in output_list:
                        exprs.extend(get_text_exprs(o))
                elif isinstance(output_list, dict):
                    for o in output_list:
                        for e in output_list[o]:
                            exprs.extend(get_text_exprs(e))
                return exprs
            except:
                pass
        return get_text_exprs(text)

    def parse_action(text):
        func_call_str = text.strip().split("Action: ")[-1].strip()
        func_call_str = re.search(r"\w+\(.*\)", func_call_str).group()
        func_call_str = func_call_str.replace("\\", "\\\\")
        func_call = ast.parse(func_call_str).body[0].value
        func_name = func_call.func.id
        func_args = [ast.literal_eval(arg) for arg in func_call.args]
        return func_call_str, func_name, func_args

    exprs = []
    if isinstance(text, list):
        for t in text:
            line = t["content"]
            line = line.replace("\\", "\\\\")
            if line.startswith("Action:"):
                try:
                    _, _, func_args = parse_action(line)
                    curr_exprs = flatten_list(func_args)
                except:
                    curr_exprs = extract_exprs_cot(line)
                    # curr_exprs = []
                exprs.extend(curr_exprs)
            else:
                line = (
                    line.replace("Output: ", "").replace("Final Answer: ", "").strip()
                )
                exprs.extend(get_exprs(line))
    exprs = flatten_list(exprs)
    exprs = [e if isinstance(e, str) else str(e) for e in exprs]
    exprs = [split_chinese(e) for e in exprs]
    exprs = flatten_list(exprs)
    # print(exprs)
    exprs = [e.replace('"', "") for e in exprs if len(e) > 0]
    return list(dict.fromkeys(exprs))


def extract_exprs_cot(text):
    pattern = r"\$(.*?)\$"
    exprs = re.findall(pattern, text)
    for i in range(len(exprs)):
        el = exprs[i].split("=")
        if len(el) > 2:
            exprs[i] = f"{el[0]} = {el[-1]}"
        exprs[i] = exprs[i].strip(" =，。")
    return exprs


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


def is_equal(ans_p, ans_l):
    if ans_p is None or ans_l is None:
        return False
    if isinstance(ans_l, str):
        return ans_p == ans_l
    if ans_p.free_symbols != ans_l.free_symbols:
        return False
    if ans_p == ans_l:
        return True
    try:
        ret = my_equals(ans_p, ans_l)
        return bool(ret)
    except:
        return False


def cal_sample_expracc(
    steps, answer, ref_answer, ref_exprs, ref_node_link, extract_exprs_fn
):
    def is_recall(ref_expr):
        if ref_expr.replace(" ", "") in exprs_nosp:
            return True
        try:
            ref_expr_sp = parse_expr(ref_expr)
        except:
            return False
        for e in exprs:
            try:
                e_sp = parse_expr(e)
            except Exception as ex:
                print(ex)
                continue
            if is_equal(ref_expr_sp, e_sp):
                return True
        return False

    def parse_expr(expr):
        expr = clean_expr_str(expr)
        expr_ns = expr.replace(" ", "")
        if expr_ns in sp_exprs:
            return sp_exprs[expr_ns]
        sp_exprs[expr_ns] = my_parse_latex(expr)
        return sp_exprs[expr_ns]

    def is_original_expr(expr):
        if expr.replace(" ", "") in origin_ref_exprs_nosp:
            return True
        try:
            expr_sp = parse_expr(expr)
        except:
            return True
        for oe in origin_ref_exprs_nosp:
            try:
                oe_sp = parse_expr(oe)
            except:
                continue
            if expr_sp == oe_sp:
                return True
        return False

    sp_exprs = {}
    score = compare_ans(answer, ref_answer)
    if score == 1:
        return 1.0, []
    # Load graph
    G = nx.node_link_graph(ref_node_link)
    rels = nx.get_edge_attributes(G, "rel")
    edges_to_remove = []
    nl_nodes = []
    # Remove useless ancestor for computing ExprAcc
    for edge in G.edges():
        if rels[edge] == "提取因式参考":
            edges_to_remove.append(edge)
        elif "描述" in rels[edge] and rels[edge] != "被描述":
            nl_nodes.append(edge[0])
    for edge in edges_to_remove:
        G.remove_edge(*edge)
    isolated_nodes = list(nx.isolates(G))
    G.remove_nodes_from(isolated_nodes)
    # Existing expr + description
    origin_ref_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
    # Existing expr
    origin_ref_exprs = [n for n in origin_ref_nodes if n not in nl_nodes]
    origin_ref_exprs_nosp = [e.replace(" ", "") for e in origin_ref_exprs]

    # Extract exprs from solution
    exprs = extract_exprs_fn(steps)
    # Remove existing or invalid expressions
    exprs = [e for e in exprs if not is_original_expr(e)]
    G.remove_nodes_from(origin_ref_nodes)

    exprs_nosp = [e.replace(" ", "") for e in exprs]
    recall_ref_exprs = set()

    # Calculate ExprAcc
    for ref_expr in ref_exprs[:-1][::-1]:
        if ref_expr in recall_ref_exprs:
            continue
        if is_recall(ref_expr):
            pre_exprs = nx.ancestors(G, ref_expr)
            pre_exprs.add(ref_expr)
            recall_ref_exprs.update(pre_exprs)
    recall_ref_exprs = list(recall_ref_exprs)
    return safe_divide(len(recall_ref_exprs), len(ref_exprs)), recall_ref_exprs
