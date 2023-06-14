import copy
import datetime
from typing import Any, Dict

from src.utils.tool_utils import (
    calculate,
    solve,
    subs,
    solve_eq,
    solve_ineq,
    solve_multi_eq,
    solve_multi_ineq,
    partial_solve,
    expand,
    factor,
    collect,
    finish,
    complete_the_square,
    mod,
    base_conversion,
    is_equal
)


class GenericRuntime:
    GLOBAL_DICT = {}
    LOCAL_DICT = None
    HEADERS = []

    def __init__(self):
        self._global_vars = copy.copy(self.GLOBAL_DICT)
        self._local_vars = copy.copy(self.LOCAL_DICT) if self.LOCAL_DICT else None

        for c in self.HEADERS:
            self.exec_code(c)

    def exec_code(self, code_piece: str) -> None:
        exec(code_piece, self._global_vars)

    def eval_code(self, expr: str) -> Any:
        return eval(expr, self._global_vars)

    def inject(self, var_dict: Dict[str, Any]) -> None:
        for k, v in var_dict.items():
            self._global_vars[k] = v

    @property
    def answer(self):
        return self._global_vars["answer"]

class ApiRuntime(GenericRuntime):
    GLOBAL_DICT = {
        "calculate": calculate,
        "solve_eq": solve_eq,
        "solve_multi_eq": solve_multi_eq,
        "solve_ineq": solve_ineq,
        "solve_multi_ineq": solve_multi_ineq,
        "partial_solve": partial_solve,
        "subs": subs,
        "substitute": subs,
        "expand": expand,
        "collect": collect,
        "factor": factor,
        "complete_the_square": complete_the_square,
        "mod": mod,
        "base_conversion": base_conversion,
        "is_equal": is_equal,
        "finish": finish,
    }

    def __init__(self):
        super().__init__()
