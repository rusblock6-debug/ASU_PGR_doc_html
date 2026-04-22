#!/usr/bin/env bash
set -eu
if (set -o 2>/dev/null | grep -q '^pipefail'); then
  set -o pipefail
fi

echo "Клонирование cursor-rules..."

cursor_rules_line=$(grep "^cursor-rules" repos.list)
if [ -z "$cursor_rules_line" ]; then
  echo "Ошибка: cursor-rules не найден в repos.list"
  exit 1
fi

cursor_rules_url=$(echo "$cursor_rules_line" | awk '{print $2}')

echo "==> cursor-rules: $cursor_rules_url"

if [ -d "../cursor-rules/.git" ]; then
  echo "    Репозиторий cursor-rules уже существует, обновляем..."
  git -C "../cursor-rules" fetch
  git -C "../cursor-rules" pull --ff-only
else
  echo "    Клонируем cursor-rules..."
  git clone --recurse-submodules "$cursor_rules_url" "../cursor-rules"
fi

echo "Клонирование cursor-rules завершено!"
