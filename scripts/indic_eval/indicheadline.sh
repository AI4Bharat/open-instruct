export CUDA_VISIBLE_DEVICES=0


model_names=(
    "manishiitg/open-aditi-hi-v2"
    "manishiitg/open-aditi-hi-v1"
)
FOLDER_BASE=/sky-notebook/eval-results


for model_name_or_path in "${model_names[@]}"; do
    model_name=${model_name_or_path##*/}
    TASK_NAME=indicheadline
    NUM_SHOTS=0short
    
    FOLDER="${FOLDER_BASE}/${TASK_NAME}/${model_name}/${NUM_SHOTS}"
    FILE=$FOLDER/metrics.json

    if [ ! -f "$FILE" ]; then
        # 1-shot
        python3 -m eval.indicheadline.run_eval \
        --ntrain 1 \
        --max_context_length 512 \
        --save_dir $FOLDER \
        --model_name_or_path $model_name_or_path \
        --tokenizer_name_or_path $model_name_or_path \
        --eval_batch_size 1 \
        --use_chat_format \
        --chat_formatting_function eval.templates.create_prompt_with_chatml_format
    fi
done