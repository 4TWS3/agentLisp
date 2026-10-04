#!/usr/bin/env bash
# temporalio/auto-setup:1.24.0 需要 default + visibility 两个 PostgreSQL 库，
# 而 postgres 官方镜像只通过 POSTGRES_DB 创建 1 个，所以这里用 initdb.d 脚本补齐第二个。
set -euo pipefail

for db in temporal temporal_visibility; do
  echo "[init-temporal-dbs] ensuring database exists: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<SQL
SELECT 'CREATE DATABASE $db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
SQL
done

for db in temporal temporal_visibility; do
  echo "[init-temporal-dbs] granting temporal user privileges on $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$db" <<SQL
GRANT ALL PRIVILEGES ON SCHEMA public TO temporal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO temporal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO temporal;
SQL
done

echo "[init-temporal-dbs] done"
