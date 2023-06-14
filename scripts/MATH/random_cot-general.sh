set -ex

python -m src.run_cot \
    --model_name gpt-3.5-turbo \
    --answer_prefix "The answer is: " \
    --step_col steps \
    --data_path data/MATH/$1/test.json \
    --demo_path data/MATH/$1/demo.json \
    --output_path eval_results/$1-random_cot.json \
    --prompt_type en \
