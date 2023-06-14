set -ex

DATA_NAME="sat-math"

python -m src.run_iter \
    --model_name gpt-3.5-turbo \
    --step_col steps \
    --data_path eval_results/$DATA_NAME-random_cot.json \
    --output_path eval_results/$DATA_NAME-deli.json \
    --prompt_path prompts/agieval/$DATA_NAME/deli-react.txt \
    --reflect_prompt_path prompts/agieval/$DATA_NAME/deli-cot.txt \
    --message_schema prompts/schema/en_schema.txt \
    --system_msg_path prompts/agieval/$DATA_NAME/deli-react-system.txt \
    --reflect_system_msg_path prompts/agieval/$DATA_NAME/deli-cot-system.txt \
    --reflect_type iter \
    --drop_system \
    --do_reverse_role \
    --answer_prefix "The answer is: " \
    --case_spliter "===" \
