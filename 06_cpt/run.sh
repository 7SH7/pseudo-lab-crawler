#!/bin/bash
# CPT 중형 모델 학습 실행 스크립트
# 담당자: 김승환
#
# 사용:
#   bash run.sh                    # 단일 GPU (CUDA_VISIBLE_DEVICES=0)
#   CUDA_VISIBLE_DEVICES=0,1,2,3 bash run.sh   # 멀티 GPU 자동 대응
#   bash run.sh path/to/other_config.yaml      # 다른 config 파일

set -e

export TOKENIZERS_PARALLELISM=false
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

CONFIG_PATH="${1:-config.yaml}"

NUM_GPUS=$(echo $CUDA_VISIBLE_DEVICES | tr ',' '\n' | wc -l)

echo "================================================================"
echo "CPT 중형 모델 학습 시작"
echo "  Config:  $CONFIG_PATH"
echo "  GPUs:    $CUDA_VISIBLE_DEVICES ($NUM_GPUS장)"
echo "================================================================"

if [ "$NUM_GPUS" -le 1 ]; then
    python train.py --config "$CONFIG_PATH"
else
    accelerate launch --num_processes="$NUM_GPUS" train.py --config "$CONFIG_PATH"
fi
