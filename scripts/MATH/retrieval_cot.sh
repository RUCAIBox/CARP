set -ex

DATA_NAME="algebra"
# DATA_NAME="prealgebra"
# DATA_NAME="counting_and_probability"
# DATA_NAME="number_theory"

python -m src.run_cot \
    --model_name gpt-3.5-turbo \
    --answer_prefix "The answer is: " \
    --step_col steps \
    --data_path data/MATH/$DATA_NAME/test.json \
    --demo_path data/MATH/$DATA_NAME/demo.json \
    --output_path eval_results/$DATA_NAME-retrieval_cot.json \
    --do_retrieval \
    --ret_path ret_base/$DATA_NAME.json \
    --prompt_type en \
