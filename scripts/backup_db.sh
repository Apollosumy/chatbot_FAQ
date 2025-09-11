#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="/srv/app/chat_bot"
BACKUP_DIR="$PROJECT_DIR/backups/db"
DOCKER="$(command -v docker)"

# Місця, де може бути .env
CANDIDATES=(
  "$PROJECT_DIR/.env"
  "$PROJECT_DIR/chatbot_project/.env"
)

mkdir -p "$BACKUP_DIR"

# ---- контейнер БД
DB_CONT=$("$DOCKER" compose -f "$PROJECT_DIR/docker-compose.yml" ps -q db || true)
if [ -z "${DB_CONT:-}" ]; then
  echo "[ERR] Контейнер 'db' не знайдено" >&2
  exit 1
fi

# ---- витягуємо змінні з .env (якщо є)
POSTGRES_NAME=""; POSTGRES_USER=""; POSTGRES_PASSWORD=""
for ENV_FILE in "${CANDIDATES[@]}"; do
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(POSTGRES_NAME|POSTGRES_USER|POSTGRES_PASSWORD)=' "$ENV_FILE" | xargs) || true
  fi
done
POSTGRES_NAME="${POSTGRES_NAME:-}"
POSTGRES_USER="${POSTGRES_USER:-}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# ---- fallback з env контейнера БД
if [ -z "$POSTGRES_NAME" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
  cDB=$("$DOCKER" exec -i "$DB_CONT" printenv POSTGRES_DB || true)
  cUSER=$("$DOCKER" exec -i "$DB_CONT" printenv POSTGRES_USER || true)
  cPASS=$("$DOCKER" exec -i "$DB_CONT" printenv POSTGRES_PASSWORD || true)
  POSTGRES_NAME="${POSTGRES_NAME:-$cDB}"
  POSTGRES_USER="${POSTGRES_USER:-$cUSER}"
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$cPASS}"
fi

if [ -z "$POSTGRES_NAME" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ]; then
  echo "[ERR] Не можу визначити POSTGRES_* (ані з .env, ані з контейнера)" >&2
  exit 1
fi

STAMP=$(date +%F_%H%M)
OUT="$BACKUP_DIR/${POSTGRES_NAME}_${STAMP}.dump.gz"

echo "[INFO] Старт бекапу ${POSTGRES_NAME} -> $OUT"

# pg_dump з контейнера БД, стискаємо на хості
"$DOCKER" exec -e PGPASSWORD="$POSTGRES_PASSWORD" -i "$DB_CONT" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_NAME" -F c \
| gzip -c > "$OUT"

# Валідація та ретенція
gzip -t "$OUT"
echo "[OK] Бекап готовий: $OUT"

# Прибирання старших за 10 днів
find "$BACKUP_DIR" -type f -name '*.dump.gz' -mtime +10 -print -delete \
  | sed 's/^/[GC] /' || true
