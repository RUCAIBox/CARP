set -ex

python -m src.run_cot \
    --model_name gpt-3.5-turbo \
    --answer_prefix "The answer is: " \
    --step_col steps \
    --data_path data/agieval/sat-math/test.json \
    --demo_path data/agieval/sat-math/demo.json \
    --output_path eval_results/sat-math-random_cot.json \
    --prompt_type en \
