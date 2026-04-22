#!/bin/bash

# Скрипт для запуска тестов в Docker контейнере
# Использование:
#   ./run_tests.sh                    # Запустить все тесты
#   ./run_tests.sh tasks/unit         # Запустить тесты из конкретной директории
#   ./run_tests.sh -v                 # Запустить с verbose выводом
#   ./run_tests.sh -k test_create     # Запустить тесты, содержащие "test_create"
#   ./run_tests.sh --pdb              # Запустить с отладчиком
#   CONTAINER_NAME=my-container ./run_tests.sh  # Указать имя контейнера

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Определяем имя контейнера (можно переопределить через переменную окружения)
CONTAINER_NAME="${CONTAINER_NAME:-dispatching-trip-service}"

# Определяем рабочую директорию в контейнере
CONTAINER_WORKDIR="/app"

# Определяем путь к тестам в контейнере
TESTS_PATH="${CONTAINER_WORKDIR}/app/tests"

# Функция для проверки существования контейнера
check_container() {
    if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}Ошибка: Контейнер '${CONTAINER_NAME}' не запущен${NC}"
        echo "Запустите контейнер перед выполнением тестов"
        echo ""
        echo "Доступные контейнеры:"
        docker ps --format "  {{.Names}}"
        exit 1
    fi
}

# Функция для проверки наличия pytest
check_pytest() {
    local docker_cmd=$(get_docker_cmd)
    if ! $docker_cmd bash -c "cd ${CONTAINER_WORKDIR} && python -m pytest --version" >/dev/null 2>&1; then
        echo -e "${RED}Ошибка: pytest не установлен в контейнере${NC}"
        exit 1
    fi
}

# Функция для определения команды docker
get_docker_cmd() {
    # Проверяем, есть ли docker-compose в корне проекта
    local project_root=$(find_project_root)
    if [ -n "$project_root" ]; then
        cd "$project_root"
        if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
            # Пробуем определить имя сервиса из docker-compose
            SERVICE_NAME=$(docker-compose ps --services 2>/dev/null | grep -i "trip\|backend\|app" | head -1)
            if [ -n "$SERVICE_NAME" ]; then
                echo "docker-compose exec -T $SERVICE_NAME"
                return
            fi
        fi
    fi

    # Используем docker exec
    echo "docker exec -i ${CONTAINER_NAME}"
}

# Функция для поиска корня проекта (где может быть docker-compose)
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/docker-compose.yml" ] || [ -f "$dir/docker-compose.yaml" ]; then
            echo "$dir"
            return
        fi
        dir=$(dirname "$dir")
    done
}

# Функция для парсинга аргументов
parse_args() {
    local test_path=""
    local pytest_args=()
    local path_found=false

    for arg in "$@"; do
        if [[ "$arg" =~ ^- ]] || [ "$path_found" = true ]; then
            # Это опция pytest или уже нашли путь
            pytest_args+=("$arg")
        else
            # Это путь к тестам
            test_path="$arg"
            path_found=true
        fi
    done

    echo "$test_path|${pytest_args[*]}"
}

# Функция для запуска тестов
run_tests() {
    local docker_cmd=$(get_docker_cmd)
    local parsed=$(parse_args "$@")
    local test_path=$(echo "$parsed" | cut -d'|' -f1)
    local pytest_args_str=$(echo "$parsed" | cut -d'|' -f2)

    # Определяем путь к тестам
    local full_test_path="${TESTS_PATH}"
    if [ -n "$test_path" ]; then
        full_test_path="${TESTS_PATH}/${test_path}"
    fi

    # Если нет аргументов pytest, добавляем стандартные опции
    if [ -z "$pytest_args_str" ]; then
        pytest_args_str="-v"
    fi

    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Запуск тестов в контейнере '${CONTAINER_NAME}'${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Путь к тестам: ${full_test_path}${NC}"
    echo -e "${YELLOW}Аргументы pytest: ${pytest_args_str}${NC}"
    echo ""

    # Запускаем тесты
    $docker_cmd bash -c "cd ${CONTAINER_WORKDIR} && python -m pytest ${full_test_path} ${pytest_args_str}"
}

# Основная логика
main() {
    check_container
    check_pytest
    run_tests "$@"
}

# Запуск
main "$@"
