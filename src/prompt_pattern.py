import dataclasses


@dataclasses.dataclass
class FewShotPattern:
    """Patterns for few-shot tasks.

    The few-shot input are composed by a few examplers followed by final_suffix:
    {final_prefix} {exampler no. 1} + {exampler no. 2} + {exampler no. 3}... + {final_suffix}

    Each exampler has the following format:
    {inputs_prefix} + {inputs} + {x_y_delimiter} + {targets_prefix} + {targets} +
    {example_separator}
    """

    inputs: str
    targets: str
    inputs_prefix: str = ""
    targets_prefix: str = ""
    x_y_delimiter: str = "\n\n"
    example_separator: str = "\n\n\n"
    final_prefix: str = ""
    final_suffix: str = ""
    input_pattern: str = "{{inputs}}{final_suffix}"
    in_template_mix: bool = True

    @property
    def few_shot_kwargs(self):
        return dict(
            inputs_prefix=self.inputs_prefix,
            targets_prefix=self.targets_prefix,
            x_y_delimiter=self.x_y_delimiter,
            example_separator=self.example_separator,
            final_suffix=self.final_suffix,
            input_pattern=self.input_pattern,
        )

    @property
    def combined_inputs(self):
        return self.inputs_prefix + self.inputs + self.x_y_delimiter

    @property
    def combined_targets(self):
        return self.targets_prefix + self.targets + self.example_separator

    @property
    def combined_inputs_w_target_prefix(self):
        return (
            self.inputs_prefix
            + self.inputs
            + self.x_y_delimiter
            + (self.targets_prefix)
        )

    @property
    def combined_targets_wo_target_prefix(self):
        return self.targets + self.example_separator


COT_PATTERNS = {
    "zh": FewShotPattern(
        inputs="{question}",
        targets="{chain_of_thought} 答案是：{answer}",
        x_y_delimiter="\n",
        example_separator="\n\n",
        inputs_prefix="问题: ",
        targets_prefix="解答: ",
        final_prefix="""You are a helpful assistant for solving Chinese math problems in LaTeX format.

""",
    ),
    "en": FewShotPattern(
        inputs="{question}",
        targets="{chain_of_thought} The answer is: {answer}",
        x_y_delimiter="\n",
        example_separator="\n\n",
        inputs_prefix="Question: ",
        targets_prefix="Answer: ",
    ),
}

BOOTSTRAPS = {
    "math_en": {
        "role": "user",
        "content": "You are a helpful expert for math problem solving.",
    },
    "math_en_code": {
        "role": "user",
        "content": "You are a helpful expert using python for math problem solving.",
    },
}
