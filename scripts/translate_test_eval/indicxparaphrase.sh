


# Llama-2 7B Base Checkpoint
model_name_or_path="meta-llama/Llama-2-7b-hf"
echo "evaluating llama 2 base on indicxparaphrase ..."

# zero-shot
python3 -m eval.indicxparaphrase.run_translate_test_eval \
    --ntrain 0 \
    --save_dir "/sky-notebook/eval-results/translate_test/llama-2/indicxparaphrase/llama-2-7b-0shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 8

# 5-shot
python3 -m eval.indicxparaphrase.run_translate_test_eval \
    --ntrain 5 \
    --save_dir "/sky-notebook/eval-results/translate_test/llama-2/indicxparaphrase/llama-2-7b-0shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 4


# Llama-2 7B Chat Checkpoint
model_name_or_path="meta-llama/Llama-2-7b-chat-hf"

echo "evaluating llama 2 chat on indicxparaphrase ..."

# zero-shot
python3 -m eval.indicxparaphrase.run_translate_test_eval \
    --ntrain 0 \
    --save_dir "/sky-notebook/eval-results/translate_test/llama-2/indicxparaphrase/llama-2-7b-chat-0shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 8 \
    --use_chat_format \
    --chat_formatting_function eval.templates.create_prompt_with_llama2_chat_format

# 5-shot
python3 -m eval.indicxparaphrase.run_translate_test_eval \
    --ntrain 5 \
    --save_dir "/sky-notebook/eval-results/translate_test/llama-2/indicxparaphrase/llama-2-7b-chat-5shot" \
    --model_name_or_path $model_name_or_path \
    --tokenizer_name_or_path $model_name_or_path \
    --eval_batch_size 4 \
    --use_chat_format \
    --chat_formatting_function eval.templates.create_prompt_with_llama2_chat_format

