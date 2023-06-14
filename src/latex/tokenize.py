# coding=utf-8
import unicodedata

from src.latex import parse_unimathsymbols


unimathsymbols = parse_unimathsymbols.read_data()


def customize_category(c):
    """
    自定义字符类别，为了后续进行文本分割
    """
    CJK_Radicals = (11904, 42191)
    category = unicodedata.category(c)

    if c == "\\":
        new_category = "Escape"
    elif category[:1] == "N":
        new_category = "Number"
    elif ord(c) in unimathsymbols:
        new_category = unimathsymbols[ord(c)].math_class
    elif CJK_Radicals[0] <= ord(c) <= CJK_Radicals[1]:
        new_category = "Chinese_" + category[:1]
    else:
        new_category = "Other"
    return new_category


def is_chinese(c):
    if customize_category(c).startswith("Chinese"):
        return True
    else:
        return False


def tokenize_latex_text(unistr):
    if unistr == "":
        return []

    pre_category = ""
    stack = []

    ret = []
    for c in unistr:
        cur_category = customize_category(c)

        if pre_category != "Escape" and cur_category != pre_category:
            if stack:
                ret.append("".join(stack))
            stack = []
            stack.append(c)
        elif pre_category != "Escape" and cur_category == pre_category:
            stack.append(c)
        elif pre_category == "Escape":
            if c != " ":
                stack.append(c)
        pre_category = cur_category

    if stack:
        ret.append("".join(stack))

    ret = [r for r in ret if r != " "]

    return ret
