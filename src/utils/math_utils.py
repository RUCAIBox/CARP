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
import timeout_decorator
import mpmath

import sympy as sp
from sympy.parsing.latex import parse_latex
import sympy as sp
from sympy import simplify
from sympy.printing import latex
from sympy.core.relational import Relational
from sympy.solvers.solveset import solvify
from sympy.solvers.inequalities import reduce_inequalities
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication,
)

transformations = standard_transformations + (implicit_multiplication,)


from src.latex.tokenize import tokenize_latex_text

RE_PATTERNS = {
    "infty": re.compile(
        r"(\s且)?\s*([a-z] [<>] -?\\infty|-?\\infty [<>] [a-z])\s*(且\s)?"
    ),
}


def my_parse_latex(expr_str):
    expr_str = expr_str.replace("dfrac", "frac")
    expr = parse_latex(expr_str)
    if "\\pi" in expr_str:
        expr = expr.subs({sp.Symbol("pi"): sp.pi})
    expr = expr.subs({sp.Symbol("i"): sp.I})
    return expr


def is_number(element: str) -> bool:
    try:
        float(element.replace(" ", ""))
        return True
    except ValueError:
        return False


def percentage_to_fraction(text):
    pattern = r"(\d+(\.\d+)?%)"
    matches = re.findall(pattern, text)
    for match in matches:
        percentage_str = match[0]
        percentage = float(percentage_str.strip("%")) / 100
        fraction = str(percentage)
        text = text.replace(percentage_str, fraction)
    return text


def clean_expr_str(expr_str):
    expr_str = (
        expr_str.replace(" . ", ".")
        .replace(". ", ".")
        .replace("**", "^")
        .replace("\\pm", "")
        .replace("*", "\\times ")
        .replace("\\\\", "\\")
        .replace("\\ne ", "\\neq ")
        .replace("!=", "\\neq")
        .replace(">=", "\\ge")
        .replace("<=", "\\le")
        .replace("≠", "\\neq")
        .replace("dfrac", "frac")
        .replace("tfrac", "frac")
        .replace("\\$", "")
        .replace("$", "")
        .replace("\\%", "")
        .replace("%", "")
        .replace("\\!", "")
        .replace("^\circ", "\\times \\pi / 180")
        .replace("//", "/")
        .replace('"', "")
    )
    expr_str = re.sub(r"\\+", r"\\", expr_str)
    expr_str = re.sub(r"\^\s?\((.*?)\)", r"^{\1}", expr_str)
    expr_str = re.sub(r"\\frac\s?(\d)\s?(\d+)", r"\\frac{\1}{\2}", expr_str)
    expr_str = re.sub(r"\\log_\s?(\d)\s?(\d+)", r"\\log_{\1}{\2}", expr_str)
    expr_str = re.sub(r"\\frac\s?{(.*?)}\s?(\d)", r"\\frac{\1}{\2}", expr_str)
    expr_str = re.sub(r"\\frac\s?(\d)\s?{(.*?)}", r"\\frac{\1}{\2}", expr_str)
    expr_str = re.sub(r"\\sqrt\s?(\d)", r"\\sqrt{\1}", expr_str)
    expr_str = re.sub(r"sqrt\s?\((\d+)\)", r"\\sqrt{\1}", expr_str)
    expr_str = re.sub(r"sqrt\s?\((.*?)\)", r"\\sqrt{\1}", expr_str)
    expr_str = expr_str.replace(" sqrt", "\\sqrt")
    expr_str = (
        expr_str.replace("\\left", "").replace("\\right.", "").replace("\\right", "")
    )
    return expr_str


def parse_latex_answer(sample):
    if isinstance(sample, int) or isinstance(sample, float):
        sample = str(sample)
    #     return sample
    sample = clean_expr_str(sample)
    try:
        expr = my_parse_latex(sample)
    except:
        print("[parse failed]", sample)
        return None
    return expr


def my_equals(ans_p, ans_l):
    return ans_p.equals(ans_l)


def is_expr_equal(ans_p, ans_l, is_strict=False):
    def is_equ_num_equal(equation, number):
        if (
            isinstance(equation, sp.Eq)
            # and isinstance(equation.lhs, sp.Symbol)
            and equation.rhs.is_number
            and number.is_number
        ):
            try:
                ret = my_equals(equation.rhs, number)
                return bool(ret)
            except:
                return equation.rhs == number

    if ans_p is None or ans_l is None:
        return False
    if isinstance(ans_l, str):
        return ans_p == ans_l

    if (
        not is_strict
        and is_equ_num_equal(ans_l, ans_p)
        or is_equ_num_equal(ans_p, ans_l)
    ):
        return True

    if ans_p.free_symbols != ans_l.free_symbols:
        return False

    if ans_p == ans_l:
        return True

    if isinstance(ans_l, sp.core.relational.Relational):
        try:
            if (
                type(ans_l) == type(ans_p)
                and my_equals(ans_p.lhs, ans_l.lhs)
                and my_equals(ans_p.rhs, ans_l.rhs)
            ):
                return True
        except Exception as e:
            print(ans_p, ans_l, e)
    try:
        ret = my_equals(ans_p, ans_l)
        return bool(ret)
    except:
        return False


@timeout_decorator.timeout(5)
def compare_ans(ans_p_str, ans_l_str, is_strict=False):
    ans_p_str = clean_expr_str(ans_p_str)
    ans_p_str = ans_p_str.replace(",", "").replace("$", "")
    ans_l_str = clean_expr_str(ans_l_str)
    ans_l_str = ans_l_str.replace(",", "").replace("$", "")
    if ans_p_str is None:
        return False
    if ans_p_str.replace(" ", "") == ans_l_str.replace(" ", ""):
        return True
    ans_p = parse_latex_answer(ans_p_str)
    if ans_p is None:
        return False
    ans_l = parse_latex_answer(ans_l_str)
    if ans_l is None:
        return False
    return is_expr_equal(ans_p, ans_l, is_strict=is_strict)


def try_integer(expr):
    if hasattr(expr, "is_number") or not expr.is_number:
        return expr
    int_expr = sp.Integer(expr)
    if expr == int_expr:
        return int_expr
    return expr


def sympy_to_latex(expr, do_simplify=True):
    if do_simplify and isinstance(expr, sp.core.relational.Relational):
        expr = my_simplify(expr)
    expr = try_integer(expr)
    ret = latex(expr)
    ret = (
        ret.replace("\\left", "")
        .replace("\\right", "")
        .replace("\\vee", "或")
        # .replace("\\wedge", "且")
        .replace("\\leq", "\\le")
        .replace("\\geq", "\\ge")
    )
    ret = RE_PATTERNS["infty"].sub("", ret)
    ret = ret.strip()
    while ret[0] == "且" or ret[-1] == "且":
        ret = ret.strip("且").strip()
    ret = " ".join(tokenize_latex_text(ret)).replace(" . ", ".")
    return ret


def ans2str(num, do_simplify=True):
    return sympy_to_latex(num, do_simplify=do_simplify)


def solve_ans2str(solve_ans, symbols=None):
    def get_unkown_symbol(expr):
        left_expr = expr.args[0]
        if left_expr.is_Relational:
            return left_expr.lhs if left_expr.lhs.is_symbol else left_expr.rhs
        return get_unkown_symbol(left_expr)

    if isinstance(solve_ans, list):
        if len(solve_ans) == 0:
            return ""
        if isinstance(solve_ans[0], dict):
            ans_dict = {}
            for ans in solve_ans:
                for key in ans:
                    if key not in ans_dict:
                        ans_dict[key] = []
                    ans_dict[key].append(f"{key} = {ans2str(ans[key])}")
            ans_strs = []
            for key in ans_dict:
                ans_strs.append(" 或 ".join(ans_dict[key]))
            return " , ".join(ans_strs)

        # solveset for equations
        assert len(symbols) == 1, (symbols, solve_ans)
        anses = [f"{symbols[0]} = {ans2str(a)}" for a in solve_ans]
        return " 或 ".join(anses)

    assert isinstance(solve_ans, sp.Basic), solve_ans
    if solve_ans.is_Boolean:
        symbol = get_unkown_symbol(solve_ans)
        solve_ans = solve_ans.subs(
            {
                sp.Lt(symbol, sp.oo): True,
                sp.Lt(-sp.oo, symbol): True,
                sp.Gt(symbol, -sp.oo): True,
                sp.Gt(sp.oo, symbol): True,
            }
        )
    ans_str = sympy_to_latex(solve_ans, do_simplify=False)
    return ans_str


@timeout_decorator.timeout(5, use_signals=False)
def my_simplify(expr):
    return simplify(expr)


def my_parse_latex(expr_str):
    def reparse(expr):
        if not isinstance(expr, Relational):
            expr = sp.parse_expr(
                str(expr),
                transformations=transformations,
            )
            return expr
        lhs_expr = (
            sp.parse_expr(str(expr.lhs), transformations=transformations)
            if expr.lhs.has(sp.Function)
            else expr.lhs
        )
        rhs_expr = (
            sp.parse_expr(str(expr.rhs), transformations=transformations)
            if expr.rhs.has(sp.Function)
            else expr.rhs
        )
        expr = type(expr)(lhs_expr, rhs_expr)
        return expr

    expr_str = clean_expr_str(expr_str)
    expr = parse_latex(expr_str)
    if "\\pi" in expr_str:
        expr = expr.subs({sp.Symbol("pi"): sp.pi})
    expr = expr.subs({sp.Symbol("i"): sp.I})
    if expr.has(sp.Function):
        try:
            expr = reparse(expr)
        except:
            print("fail to reparse", expr)
    return expr


def mysolve(expr, symbol=None):
    # expr or list of exprs
    if isinstance(expr, sp.Eq):
        if expr.has(sp.I):
            solve_ans = solvify(expr, symbol=symbol, domain=sp.S.Complexes)
        else:
            solve_ans = solvify(
                expr, symbol=symbol, domain=sp.S.Reals
            )  # list `[-1, 1]`
    elif symbol is None:  # inequalities or
        solve_ans = sp.solve(
            expr,
            dict=True,
        )  # list `[{x: 1/2, y:1/2}]` or Relational `(x <= 5) & (1 < x)`
    else:  # PEQ or PINEQ
        solve_ans = reduce_inequalities(expr, symbols=[symbol])
    if symbol is not None and solve_ans is None:  # x/(x - 1*3) = (3*m)/(x - 1*3)
        lhs_frac = sp.fraction(expr.lhs)
        rhs_frac = sp.fraction(expr.rhs)
        is_lhs_frac = lhs_frac[1] != 1 and len(lhs_frac[1].free_symbols) > 0
        is_rhs_frac = rhs_frac[1] != 1 and len(rhs_frac[1].free_symbols) > 0
        if is_lhs_frac or is_rhs_frac:
            multipler = lhs_frac[1] if is_lhs_frac else rhs_frac[1]
            new_expr = type(expr)(expr.lhs * multipler, expr.rhs * multipler)
            if isinstance(expr, sp.Eq):
                solve_ans = partial_solve(expr, symbol)
            else:
                solve_ans = reduce_inequalities(new_expr, symbols=[symbol])
            assert solve_ans is not None
        elif isinstance(expr, sp.Eq):
            solve_ans = partial_solve(expr, symbol)
    return solve_ans


def partial_solve(expr, symbol):
    try:
        solve_ans = sp.solve(sp.Eq(expr.lhs - expr.rhs, 0), symbol, dict=True)
    except:
        return None
    return solve_ans


def mysubs(expr, replacements):
    # Substitutable:
    new = replacements.get(expr, None)
    if new is not None:
        return new

    # Atoms:
    args = expr.args
    if not args:
        return expr

    # Recurse:
    newargs = [mysubs(arg, replacements) for arg in expr.args]
    if newargs == args:
        return expr
    return expr.func(*newargs)


def get_symbols(expr):
    if isinstance(expr, list):
        ret_set = set()
        for e in expr:
            ret_set = ret_set.union(ret_set, e.free_symbols)
        return list(ret_set)
    return list(expr.free_symbols)
