import re
import io
import signal
import json
from contextlib import redirect_stdout
from typing import Any, Callable, List, Optional
from collections import Counter
import timeout_decorator


from src.core.runtime import GenericRuntime
from src.core.backend import call_gpt
from src.prompt_pattern import BOOTSTRAPS
from src.utils.utils import extract_cot_answer


class timeout:
    def __init__(self, seconds=1, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def timeout_handler(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


class TextInterface:
    def __init__(
        self,
        model: str = "code-davinci-002",
        answer_prefix: str = "The answer is:",
        stop: str = None,
        num_beams: int = 1,
        temperature: float = 0.0,
        extract_answer: Optional[Callable[[str], Any]] = None,
        max_tokens: int = 512,
    ):
        self.history = []
        self.answer_prefix = answer_prefix
        self.extract_answer_fn = extract_answer
        self.stop = stop
        self.model = model
        self.num_beams = num_beams
        self.temperature = temperature
        self.max_tokens = max_tokens

    def clear_history(self):
        self.history = []

    def extract_answer(self, gen: str):
        if self.extract_answer_fn:
            return self.extract_answer_fn(gen)
        last_line = gen.strip().replace("$", "").split(self.answer_prefix)[-1].strip()
        last_line = last_line.strip("。").strip(".")
        return last_line

    def run(self, prompt, bootstrap: str = None):
        gen = call_gpt(
            prompt,
            bootstrap=BOOTSTRAPS["math_en"] if bootstrap is None else bootstrap,
            model=self.model,
            stop=self.stop,
            max_tokens=self.max_tokens,
            num_beams=self.num_beams,
            temperature=self.temperature,
        )
        self.history = [gen]
        answers = [extract_cot_answer(g, answer_prefix=self.answer_prefix) for g in gen]
        counter = Counter(answers)
        return counter.most_common(1)[0][0]


class ProgramInterface:
    def __init__(
        self,
        model: str = "code-davinci-002",
        runtime: Optional[Any] = None,
        stop: str = None,
        get_answer_symbol: Optional[str] = None,
        get_answer_expr: Optional[str] = None,
        get_answer_from_stdout: bool = False,
        verbose: bool = False,
    ) -> None:
        self.model = model
        self.runtime = runtime if runtime else GenericRuntime()
        self.history = []
        self.stop = stop
        self.answer_symbol = get_answer_symbol
        self.answer_expr = get_answer_expr
        self.get_answer_from_stdout = get_answer_from_stdout
        self.verbose = verbose
        self.sys_msg = "You are a helpful python programmer."

    def clear_history(self):
        self.history = []

    def process_generation_to_code(self, gens: str):
        if "```python" in gens:
            gens = gens.split("```python")[1].split("```")[0]
        elif "```" in gens:
            gens = gens.split("```")[1].split("```")[0]
        gens = gens.replace("\\", "\\\\")

        return [gens.split("\n")]

    def generate(
        self,
        prompt: str,
        bootstrap: str = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 512,
        num_beams: int = 1,
    ):
        gens = call_gpt(
            prompt,
            bootstrap={"role": "system", "content": self.sys_msg},
            model=self.model,
            stop=self.stop,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            num_beams=num_beams,
        )[0]
        if self.verbose:
            print(gens)
        code = self.process_generation_to_code(gens)
        self.history.append(gens)
        return code

    @timeout_decorator.timeout(10)
    def execute(self, code: Optional[List[str]] = None):
        code = code if code else self.code
        if self.get_answer_from_stdout:
            program_io = io.StringIO()
            with redirect_stdout(program_io):
                self.runtime.exec_code("\n".join(code))
            program_io.seek(0)
            return program_io.readlines()[-1]
        elif self.answer_symbol:
            self.runtime.exec_code("\n".join(code))
            return self.runtime._global_vars[self.answer_symbol]
        elif self.answer_expr:
            self.runtime.exec_code("\n".join(code))
            return self.runtime.eval_code(self.answer_expr)
        else:
            self.runtime.exec_code("\n".join(code[:-1]))
            return self.runtime.eval_code(code[-1])

    def run(
        self,
        prompt: str,
        bootstrap: str = None,
        time_out: float = 10,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 512,
        num_beams: int = None,
    ):
        code_snippets = self.generate(
            prompt,
            bootstrap=bootstrap,
            num_beams=num_beams,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        results = []
        for code in code_snippets:
            with timeout(time_out):
                try:
                    exec_result = self.execute(code)
                    if not isinstance(exec_result, str):
                        exec_result = str(exec_result)
                except Exception as e:
                    print(e)
                    continue
                results.append(exec_result)
        counter = Counter(results)
        if len(results) > 0:
            return counter.most_common(1)[0][0]

        return "-10000"
