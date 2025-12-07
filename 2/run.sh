#!/bin/bash

if [ -z "$1" ]; then
    echo "Использование: $0 <количество_контейнеров>"
    echo "Пример: $0 10"
    exit 1
fi

COUNT=$1
IMAGE_NAME="concurrency-lab"
VOL_NAME="lab_shared_vol"
HOST_DATA_DIR="$(pwd)/data_output"

echo "=== Подготовка окружения ==="

echo ">> Сборка образа $IMAGE_NAME..."
docker build -q -t $IMAGE_NAME . > /dev/null

echo ">> Создание директории для данных: $HOST_DATA_DIR"
mkdir -p "$HOST_DATA_DIR"

echo ">> Создание тома $VOL_NAME..."

docker volume rm $VOL_NAME 2>/dev/null || true

docker volume create --driver local \
    --opt type=none \
    --opt device="$HOST_DATA_DIR" \
    --opt o=bind \
    "$VOL_NAME"

echo "=== Запуск контейнеров ==="
for i in $(seq 1 $COUNT); do
    CONTAINER_NAME="worker_$(printf "%03d" $i)"
    echo "Запускаем $CONTAINER_NAME..."

    docker run -d --rm --name "$CONTAINER_NAME" \
        -v "$VOL_NAME":/data \
        $IMAGE_NAME > /dev/null
done

echo ""
echo "=== Тест запущен ==="
echo "Запущено $COUNT контейнеров."
echo "Файлы создаются в папке: $HOST_DATA_DIR"
echo "Вы можете наблюдать за процессом в другом терминале: watch ls -l data_output"
echo ""
read -p "Нажмите [ENTER], чтобы остановить тест и удалить том..."

echo ""
echo "=== Завершение работы ==="

echo ">> Остановка контейнеров..."

docker stop $(docker ps -q --filter ancestor=$IMAGE_NAME) > /dev/null

sleep 3

echo ">> Удаление тома $VOL_NAME..."
docker volume rm "$VOL_NAME"