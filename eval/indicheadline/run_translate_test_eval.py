import argparse
import os
import random
import torch
import numpy as np
import pandas as pd
import time
import json
from tqdm import tqdm
import time
import evaluate
from datasets import load_dataset
from eval.utils import (
    dynamic_import_function,
)
from bleurt import score
from transformers import AutoTokenizer
import vllm
import evaluate
exact_match = evaluate.load("exact_match")

lang_map = {
    "as": "Assamese",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "hi": "Hindi",
    "ml": "Malayalam",
    "mr": "Marathi",
    "or": "Oriya",
    "pa": "Punjabi",
    "ta": "Tamil",
    "te": "Telugu",
}


def trim_context(context, max_context_length, tokenizer):
    tokenized_context = tokenizer.encode(context, add_special_tokens=False)
    if len(tokenized_context) > max_context_length:
        context = tokenizer.decode(
            tokenized_context[:max_context_length], skip_special_tokens=True, clean_up_tokenization_spaces=True
        )
    return context


def format_example(input, lang, headline=None):
    lang = "English" # lang_map[lang]
    user_prompt = f"{lang.capitalize()} article: {input}"
    assistant_prompt = f"\n{lang.capitalize()} headline:"
    if headline is not None:
        assistant_prompt += f" {headline}"
    messages = [{"role":"user", "content":user_prompt}, {"role":"assistant", "content":assistant_prompt}]
    return messages


def gen_prompt(dev_data, lang, max_context_length, tokenizer, k=-1):
    prompt = f"Generate a headline for the following article(s) as accurately as possible."
    messages = [{"role": "system", "content": prompt}]
    if k > 0:
        exemplars = dev_data.select(range(k))
        for example in exemplars:
            messages += format_example(
                input=trim_context(example["input"], max_context_length, tokenizer),
                lang=lang,
                headline=example["target"],
            )
    return messages

@torch.no_grad()
def eval_hf_model(args, model, tokenizer, prompts, test_data, batch_size=1):
    sampling_params = vllm.SamplingParams(
        temperature=0,
        max_tokens=512,
        stop=["<|im_end|>"],
    )
    # We need to remap the outputs to the prompts because vllm might not return outputs for some prompts (e.g., if the prompt is too long)
    generations = model.generate(prompts, sampling_params)

    prompt_to_output = {
        g.prompt: g.outputs[0].text.strip() for g in generations
    }
    outputs = [prompt_to_output[prompt]
               if prompt in prompt_to_output else "" for prompt in prompts]

    return outputs

def main(args):
    random.seed(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(
        args.tokenizer_name_or_path if args.tokenizer_name_or_path else args.model_name_or_path)

    if args.use_vllm:
        if args.awq:
            print("Loading model and tokenizer vllm awq...")
            model = vllm.LLM(
                model=args.model_name_or_path,
                tokenizer=args.tokenizer_name_or_path if args.tokenizer_name_or_path else args.model_name_or_path,
                tokenizer_mode="auto",
                tensor_parallel_size=torch.cuda.device_count(),
                # max_num_batched_tokens=4096,
                quantization="AWQ",
                max_model_len=4096,
            )
        else:
            print("Loading model and tokenizer vllm...")
            model = vllm.LLM(
                model=args.model_name_or_path,
                tokenizer=args.tokenizer_name_or_path if args.tokenizer_name_or_path else args.model_name_or_path,
                tokenizer_mode="auto",
                tensor_parallel_size=torch.cuda.device_count(),
                # max_num_batched_tokens=4096,
                max_model_len=4096,
            )
    else:
        # print("Loading model and tokenizer hf...")
        # model, tokenizer = load_hf_lm_and_tokenizer(
        #     model_name_or_path=args.model_name_or_path,
        #     tokenizer_name_or_path=args.tokenizer_name_or_path,
        #     load_in_8bit=args.load_in_8bit,
        #     device_map="balanced_low_0" if torch.cuda.device_count() > 1 else "auto",
        #     gptq_model=args.gptq,
        #     use_fast_tokenizer=not args.use_slow_tokenizer,
        # )
        raise Exception("only vllm is supported")

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    chat_formatting_function = dynamic_import_function(args.chat_formatting_function) if args.use_chat_format else None

    dataset = load_dataset("ai4bharat/IndicHeadlineGeneration","hi")
            
    dataset = dataset.map(lambda x: {"input": x["input"].strip()})
    dataset = dataset.map(lambda x: {"target": x["target"].strip()})
    dev_data = dataset["validation"].select(range(min(len(dataset["validation"]), args.n_instances)))
    test_data = dataset["test"].select(range(min(len(dataset["test"]), args.n_instances)))


    test_data = test_data.select(range(10))

    k = args.ntrain
    prompts = []
    for i, example in enumerate(test_data):
        
        prompt_end = format_example(
            input=trim_context(example["input"], args.max_context_length, tokenizer), lang=args.lang
        )
        train_prompt = gen_prompt(dev_data, args.lang, args.max_context_length, tokenizer, k)
        prompt = train_prompt + prompt_end
        
        if args.use_chat_format:
            prompt = chat_formatting_function(prompt)
        else:
            prompt = "\n\n".join([x["content"] for x in prompt])
        
        prompts.append(prompt)
        

    outputs = eval_hf_model(args, model, tokenizer, prompts, test_data, args.batch_size)

    print("outputs", outputs)
    
    print("Calculating Rouge and BLEURT ...")
    rouge = evaluate.load("rouge")
    bleurt = score.BleurtScorer(args.bleurt_model_name_or_path)

    predictions = [output for output in outputs]
    references = [example["target"] for example in test_data]

    rouge_metrics = rouge.compute(predictions=predictions, references=references)
    metrics = {
        "rouge1": rouge_metrics["rouge1"],
        "rouge2": rouge_metrics["rouge2"],
        "rougeL": rouge_metrics["rougeL"],
        "bleurt": np.mean(bleurt.score(candidates=predictions, references=references)),
    }
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

    os.exit(1)
    # save results
    with open(os.path.join(args.save_dir, "metrics.json"), "w") as fout:
        json.dump(metrics, fout, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ntrain", type=int, default=1, help="number of examples to use for few-shot evaluation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--lang", type=str, default="hi", choices=["as", "bn", "gu", "kn", "hi", "ml", "mr", "or", "pa", "ta", "te"]
    )
    parser.add_argument("--save_dir", type=str, default="/sky-notebook/eval-results/indicheadline/llama-7B/")
    parser.add_argument(
        "--bleurt_model_name_or_path",
        type=str,
        default="./BLEURT-20",
        help="bleurt model to load for evaluation.",
    )
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="None",
        help="if specified, we will load the model to generate the predictions.",
    )
    parser.add_argument(
        "--tokenizer_name_or_path",
        type=str,
        default=None,
        help="if specified, we will load the tokenizer from here.",
    )
    parser.add_argument(
        "--max_context_length", type=int, default=768, help="maximum number of tokens in the context passage."
    )
    parser.add_argument(
        "--n_instances",
        type=int,
        default=1000,
        help="if specified, a maximum of n_instances will be used for the evaluation."
    )
    parser.add_argument("--eval_batch_size", type=int, default=1, help="batch size for evaluation.")
    parser.add_argument(
        "--load_in_8bit",
        action="store_true",
        help="load model in 8bit mode, which will reduce memory and speed up inference.",
    )
    parser.add_argument(
        "--gptq",
        action="store_true",
        help="If given, we're evaluating a 4-bit quantized GPTQ model.",
    )
    parser.add_argument(
        "--use_chat_format",
        action="store_true",
        help="If given, we will use the chat format for the prompts.",
    )
    parser.add_argument(
        "--chat_formatting_function",
        type=str,
        default="eval.templates.create_prompt_with_tulu_chat_format",
        help="The function to use to create the chat format. This function will be dynamically imported. Please see examples in `eval/templates.py`.",
    )
    parser.add_argument(
        "--awq",
        action="store_true",
        help="If given, we will use the vllm library, which will likely increase the inference throughput."
    )
    parser.add_argument(
        "--use_vllm",
        action="store_true",
        help="If given, we will use the vllm library, which will likely increase the inference throughput."
    )
    args = parser.parse_args()
    main(args)
