#!/usr/bin/env bash
set -euo pipefail

docker exec intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" -D "$MYSQL_DATABASE" -e "DESCRIBE infra_release_operation_lock; DESCRIBE infra_release_migration;"'
