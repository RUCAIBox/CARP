set -ex

python -m src.run_cot \
    --model_name gpt-3.5-turbo \
    --answer_prefix "答案是：" \
    --step_col steps \
    --data_path data/carp/test.json \
    --demo_path data/carp/demo.json \
    --output_path eval_results/carp-random_cot.json \
    --prompt_type zh \
