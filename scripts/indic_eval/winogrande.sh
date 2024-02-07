export CUDA_VISIBLE_DEVICES=0


model_name_or_path="manishiitg/open-aditi-hi-v2"

echo "evaluating open-aditi-v2 base on winogrande ..."

# zero-shot
python3 -m eval.winogrande.run_eval \
    --ntrain 0 \
    --save_dir "/sky-notebook/eval-results/winogrande/aditi-v2-0shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 8


model_name_or_path="ai4bharat/airavata"

echo "evaluating airavata on winogrande ..."

# zero-shot
python3 -m eval.winogrande.run_eval \
    --ntrain 0 \
    --save_dir "/sky-notebook/eval-results/winogrande/airavata-0shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 8 \
    --use_chat_format \
    --chat_formatting_function eval.templates.create_prompt_with_tulu_chat_format
