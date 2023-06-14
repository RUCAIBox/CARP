set -ex

python -m src.run_cot \
    --model_name gpt-3.5-turbo \
    --answer_prefix "答案是：" \
    --step_col steps \
    --data_path data/carp/test.json \
    --demo_path data/carp/demo.json \
    --output_path eval_results/carp-retrieval_cot.json \
    --do_retrieval \
    --ret_path ret_base/carp.json \
    --prompt_type zh \
