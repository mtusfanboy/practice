#!/usr/bin/env bash
#
# Скрипт инициализации (DO-07).
#
# Скачивает 10 тестовых PDF-лекций/статей из открытого доступа (arXiv) и
# загружает их в систему через REST API (POST /api/v1/documents/upload).
#
# Использование:
#   ./init.sh                      # бэкенд на http://localhost:8000
#   BACKEND_URL=http://host:8000 ./init.sh
#
# Зависимости: curl.

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
UPLOAD_ENDPOINT="${BACKEND_URL}/api/v1/documents/upload"
HEALTH_ENDPOINT="${BACKEND_URL}/health"
WORK_DIR="$(mktemp -d)"

# 10 общедоступных PDF-документов (arXiv) для наполнения базы знаний.
# При необходимости список можно переопределить переменной окружения URLS.
DEFAULT_URLS=(
  "https://arxiv.org/pdf/1706.03762"  # Attention Is All You Need
  "https://arxiv.org/pdf/1810.04805"  # BERT
  "https://arxiv.org/pdf/1512.03385"  # Deep Residual Learning (ResNet)
  "https://arxiv.org/pdf/1409.1556"   # VGG
  "https://arxiv.org/pdf/1412.6980"   # Adam Optimizer
  "https://arxiv.org/pdf/1301.3781"   # Word2Vec
  "https://arxiv.org/pdf/1406.2661"   # GANs
  "https://arxiv.org/pdf/1505.04597"  # U-Net
  "https://arxiv.org/pdf/1402.1128"   # LSTM acoustic models
  "https://arxiv.org/pdf/2005.14165"  # GPT-3: Language Models are Few-Shot Learners
)

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

log() {
  printf '[init] %s\n' "$*"
}

wait_for_backend() {
  log "Ожидание готовности бэкенда: ${HEALTH_ENDPOINT}"
  local attempts=0
  local max_attempts=60
  until curl -sf "${HEALTH_ENDPOINT}" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "${attempts}" -ge "${max_attempts}" ]; then
      log "ОШИБКА: бэкенд не ответил за $((max_attempts * 2)) секунд."
      exit 1
    fi
    sleep 2
  done
  log "Бэкенд готов."
}

main() {
  command -v curl >/dev/null 2>&1 || { log "Требуется curl."; exit 1; }

  wait_for_backend

  # Разрешаем переопределить список URL через переменную окружения URLS
  # (значения разделяются пробелами).
  local urls=("${DEFAULT_URLS[@]}")
  if [ -n "${URLS:-}" ]; then
    # shellcheck disable=SC2206
    urls=(${URLS})
  fi

  local index=0
  local uploaded=0
  local failed=0

  for url in "${urls[@]}"; do
    index=$((index + 1))
    local file_name="lecture_${index}.pdf"
    local file_path="${WORK_DIR}/${file_name}"

    log "(${index}/${#urls[@]}) Скачивание: ${url}"
    if ! curl -sfL --max-time 120 -o "${file_path}" "${url}"; then
      log "  Пропуск: не удалось скачать ${url}"
      failed=$((failed + 1))
      continue
    fi

    log "  Загрузка в систему: ${file_name}"
    if curl -sf -X POST "${UPLOAD_ENDPOINT}" \
        -F "file=@${file_path};type=application/pdf;filename=${file_name}" \
        >/dev/null; then
      uploaded=$((uploaded + 1))
    else
      log "  Ошибка загрузки ${file_name} через API."
      failed=$((failed + 1))
    fi
  done

  log "Готово. Успешно загружено: ${uploaded}, ошибок: ${failed}."
  log "Индексация выполняется в фоне; статус можно проверить:"
  log "  curl ${BACKEND_URL}/api/v1/documents"
}

main "$@"
