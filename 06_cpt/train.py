"""
CPT 중형 모델 학습 진입점
담당자: 김승환

사용:
    python train.py --config config.yaml

또는 멀티 GPU:
    accelerate launch --num_processes=4 train.py --config config.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

import torch
import yaml
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    set_seed,
)

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_corpus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="CPT 중형 모델 학습")
    p.add_argument("--config", type=str, default="config.yaml")
    return p.parse_args()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_dtype(name: str):
    return {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }[name]


def main():
    args = parse_args()
    config = load_config(args.config)

    seed = config.get("training", {}).get("seed", 42)
    set_seed(seed)

    # ─── 모델 / 토크나이저 ───
    model_name = config["model"]["base"]
    trust_remote_code = config["model"].get("trust_remote_code", True)
    logger.info(f"모델 로드: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token is None:
        # CausalLM은 EOS를 pad로 재사용 (collator는 mlm=False라 영향 없음)
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=get_dtype(config["model"].get("torch_dtype", "bfloat16")),
        trust_remote_code=trust_remote_code,
    )

    if config["training"].get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    # ─── 데이터 ───
    train_dataset = load_corpus(config, tokenizer)

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # next-token prediction
    )

    # ─── Trainer ───
    t = config["training"]
    training_args = TrainingArguments(
        output_dir=t["output_dir"],
        num_train_epochs=t.get("num_epochs", 1),
        per_device_train_batch_size=t.get("per_device_batch_size", 1),
        gradient_accumulation_steps=t.get("gradient_accumulation_steps", 16),
        learning_rate=float(t.get("learning_rate", 2e-5)),
        warmup_ratio=t.get("warmup_ratio", 0.03),
        weight_decay=t.get("weight_decay", 0.01),
        bf16=t.get("bf16", True),
        gradient_checkpointing=t.get("gradient_checkpointing", True),
        save_steps=t.get("save_steps", 1000),
        logging_steps=t.get("logging_steps", 50),
        save_total_limit=t.get("save_total_limit", 3),
        seed=seed,
        report_to="none",
        ddp_find_unused_parameters=False,
        dataloader_num_workers=4,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=collator,
        tokenizer=tokenizer,
    )

    logger.info("학습 시작")
    trainer.train()

    final_dir = Path(t["output_dir"]) / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    logger.info(f"최종 모델 저장: {final_dir}")


if __name__ == "__main__":
    main()
