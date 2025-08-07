#!/bin/bash

set -e

cd "$(dirname "$0")"

IMAGE_NAME="discord-bot-img"
CONTAINER_NAME="discord-bot-test"

if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
  echo "기존 컨테이너가 존재하여 종료 및 삭제진행"
  docker stop $CONTAINER_NAME || true
  docker rm $CONTAINER_NAME || true
fi

echo "이미지 초기화"
if docker image inspect $IMAGE_NAME > /dev/null 2>&1; then
  echo "기존 이미지가 존재하여 삭제진행"
  docker rmi $IMAGE_NAME || true
fi

echo "도커 이미지 빌드 중..."
docker build -t $IMAGE_NAME .

# Run the container with the environment variable set to 'dev'
echo "도커 컨테이너 실행 중..."
docker run -d --name $CONTAINER_NAME -e PYTHON_RUN_ENV=dev $IMAGE_NAME