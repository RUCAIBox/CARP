import re
import json
import sympy as sp
import sys
import string

import src.utils.math_utils as math_utils
from src.utils.math_utils import ans2str, sympy_to_latex, clean_expr_str, is_expr_equal

SPLIT_PATTERN = re.compile("[\u4e00-\u9fff]|[^\u4e00-\u9fff\s]+")


def parse(expr_str):
    if "mod" in expr_str or "%" in expr_str:
        expr_str = re.sub(r"\\+", r"\\", expr_str)
        expr_str = (
            expr_str.replace("\\times", "*")
            .replace("\\cdot", "*")
            .replace("^", "**")
            .replace("\\mod", "%")
            .replace("\\%", "%")
            .replace(" mod ", " % ")
        )
        print(expr_str)
        expr = sp.parse_expr(expr_str)
        return expr
    expr_str = replace_decimal(expr_str)  # TODO
    expr_str = clean_expr_str(expr_str)
    if "mod" in expr_str or "gcd" in expr_str or "\\pm" in expr_str:
        raise Exception()
    expr = math_utils.my_parse_latex(expr_str)
    if expr.has_free(sp.Symbol("f")):
        raise Exception()
    return expr


def solve_ans2str(solve_ans, symbols=None):
    def get_unkown_symbol(expr):
        left_expr = expr.args[0]
        if left_expr.is_Relational:
            return left_expr.lhs if left_expr.lhs.is_symbol else left_expr.rhs
        return get_unkown_symbol(left_expr)

    if isinstance(solve_ans, list):
        if len(solve_ans) == 0:
            raise Exception()
        if isinstance(solve_ans[0], dict):
            ans_dict = {}
            for ans in solve_ans:
                for key in ans:
                    key_str = str(key)
                    if key_str not in ans_dict:
                        ans_dict[key_str] = []
                    ans_dict[key_str].append(f"{key} = {ans2str(ans[key])}")
            return ans_dict

        # solveset for equations
        assert len(symbols) == 1, (symbols, solve_ans)
        anses = [f"{symbols[0]} = {ans2str(a)}" for a in solve_ans]
        return anses

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
        if solve_ans.is_Relational and not solve_ans.lhs.is_symbol:
            solve_ans = solve_ans.reversed
        ans_str = sympy_to_latex(solve_ans, do_simplify=False)
        return ans_str
    return [ans_str]


def calculate(expr_str: str):
    expr = parse(expr_str)
    sim_expr = math_utils.my_simplify(expr)
    sim_expr = math_utils.my_simplify(sim_expr)
    if expr.is_number:
        expr = sim_expr
        try:  # 考虑虚数
            int_expr = sp.Integer(expr)
            if int_expr == expr:
                expr = int_expr
        except:
            pass
    ans_label = f"{math_utils.ans2str(sim_expr)}"
    return ans_label


def mod(dividend_str, divisor_str):
    dividend = parse(dividend_str)
    divisor = parse(divisor_str)
    ans = dividend % divisor
    ans_label = f"{math_utils.ans2str(ans)}"
    return ans_label


def base_conversion(number, to_base):
    number, from_base = number.split("_")
    from_base = int(from_base)
    to_base = int(to_base)
    decimal_number = int(str(number), from_base)
    if from_base < 2 or to_base < 2:
        raise ValueError("Base values must be greater than or equal to 2.")

    digits = string.digits + string.ascii_uppercase
    if to_base > len(digits):
        raise ValueError("Invalid base for conversion.")

    decimal_number = int(str(number), from_base)
    converted_number = ""
    while decimal_number > 0:
        remainder = decimal_number % to_base
        converted_number = digits[remainder] + converted_number
        decimal_number //= to_base
    return (
        f"{converted_number}_{to_base}"
        if to_base < 10
        else converted_number + "_{" + str(to_base) + "}"
    )


def replace_decimal(expression):
    pattern = r"(\d+)_(\d+)"
    matches = re.findall(pattern, expression)

    if not matches:
        return expression

    decimal_numbers = []
    for number, base in matches:
        decimal_number = base_conversion(f"{number}_{base}", 10)
        decimal_numbers.append(decimal_number)

    result = expression
    for i, (number, base) in enumerate(matches):
        result = result.replace(f"{number}_{base}", decimal_numbers[i])
    result = result.replace("_{10}", "")
    return result


def is_equal(expr1_str, expr2_str):
    expr1 = parse(expr1_str)
    expr2 = parse(expr2_str)
    return is_expr_equal(expr1, expr2, is_strict=True)


def solve(expr_str):
    if isinstance(expr_str, str):
        expr = parse(expr_str)
        if expr is None:
            raise Exception()
            # return ""
    else:
        expr = []
        for es in expr_str:
            e = parse(es)
            if e is None:
                raise Exception()
                # return ""
            expr.append(e)
        if len(expr) == 1:
            expr = expr[0]
    solve_res = math_utils.mysolve(expr)
    ans_label = solve_ans2str(solve_res, math_utils.get_symbols(expr))
    return ans_label


def solve_eq(expr_str: str):
    try:
        return solve(expr_str)
    except:
        raise Exception("方程无解或含有多个未知数")


def solve_ineq(expr_str: str):
    try:
        return solve(expr_str)
    except:
        raise Exception("方程无解或含有多个未知数")


def solve_multi_eq(expr_strs: list):
    try:
        return solve(expr_strs)
    except:
        raise Exception("方程无解或给定条件不足解出方程")


def solve_multi_ineq(expr_strs: list):
    try:
        return solve(expr_strs)
    except:
        raise Exception("方程无解或给定条件不足解出方程")


def subs(expr_str, cond_strs):
    expr = parse(expr_str)
    conds = [parse(c) for c in cond_strs]
    conds = {c.lhs: c.rhs for c in conds if isinstance(c, sp.Eq)}

    def _subs(expr, conds):
        subs_expr = math_utils.mysubs(expr, conds)
        if not subs_expr.is_number:
            subs_expr = expr.subs(conds)
        subs_expr = sp.simplify(subs_expr)
        if subs_expr.is_number:
            return subs_expr
        return subs_expr

    if expr.is_Relational:
        lhs = _subs(expr.lhs, conds)
        rhs = _subs(expr.rhs, conds)
        if math_utils.is_expr_equal(expr.func(lhs, rhs), expr):
            raise Exception("代入无效上下文条件")
        if lhs == rhs:
            raise Exception("不必要调用 substitute")
        expr = expr.func(lhs, rhs)
        ans_label = math_utils.ans2str(expr)
        return ans_label

    subs_expr = _subs(expr, conds)
    if math_utils.is_expr_equal(expr, subs_expr):
        subs_expr = _subs(sp.simplify(expr), conds)
        if not subs_expr.is_number:
            symbol = list(subs_expr.free_symbols)[0]
            for k, v in conds.items():
                if symbol not in k.free_symbols and symbol not in v.free_symbols:
                    continue
                try:
                    solve_res = math_utils.mysolve(sp.Eq(k, v), symbol)
                    if len(solve_res) == 0:
                        continue
                    if isinstance(solve_res[0], dict):
                        subs_expr = _subs(subs_expr, solve_res[0])
                    else:
                        subs_expr = _subs(subs_expr, {symbol: solve_res[0]})
                    if math_utils.is_expr_equal(expr, subs_expr):
                        raise Exception("不必要调用 substitute")
                    break
                except Exception as e:
                    print(e)
                    raise Exception("不必要调用 substitute")
    ans_label = math_utils.ans2str(subs_expr)
    return ans_label


def expand(expr_str):
    expr = parse(expr_str)
    expanded_expr = sp.expand(expr)
    ans_label = math_utils.ans2str(expanded_expr)
    if expr == expanded_expr:
        raise Exception("不必要调用 expand")
    return ans_label


def factor(expr_str):
    expr = parse(expr_str)
    fac_expr = sp.factor(expr)
    ans_label = math_utils.ans2str(fac_expr)
    if expr == fac_expr:
        raise Exception("不必要调用 factor")
    return ans_label


def cts(p, x=None):
    f = sp.factor(p)
    if f.is_Pow:
        return f
    free = p.free_symbols
    n = len(free)
    if x is None:
        assert n == 1, "specify x if there is more than 1 free variable"
        x = free.pop()
    p = p.expand()
    c, d = p.as_independent(x)
    a, b = [d.coeff(i) for i in (x**2, x)]
    b /= a
    c /= a
    b2 = b / 2
    rv = a * ((x + b2) ** 2 - b2**2 + c)
    if n == 2:
        i, d = rv.as_independent(x)
        rv = cts(i) + d
    return rv


def complete_the_square(expr_str):
    expr = parse(expr_str)
    result = cts(expr)
    ans_label = math_utils.ans2str(result)
    return ans_label


def collect(expr_str, symbol_str):
    expr = parse(expr_str)
    symbol = parse(symbol_str)
    ret_expr = sp.collect(expr, symbol)
    if expr == ret_expr:
        raise Exception("不必要调用 collect")
    ans_label = math_utils.ans2str(ret_expr)
    return ans_label


def partial_solve(expr_str, symbol_str):
    expr = parse(expr_str)
    symbol = parse(symbol_str)
    try:
        solve_res = math_utils.mysolve(expr, symbol)
    except:
        raise Exception("方程无解")
    ans_label = solve_ans2str(solve_res, math_utils.get_symbols(expr))
    if isinstance(ans_label, dict):
        if len(ans_label[symbol_str]) > 1:
            return ans_label[symbol_str]
        ans_label = ans_label[symbol_str][0]
    return ans_label


def finish(answer):
    return answer
