#!/bin/bash
# Keeps a port-forward open from localhost:15432 to PostgreSQL in minikube (namespace dev).
# Reconnects automatically if the pod restarts or the connection drops.
NS=${PG_NAMESPACE:-dev}
SVC=${PG_SERVICE:-postgres-postgresql}
PORT=${PG_LOCAL_PORT:-15432}
while true; do
  kubectl -n "$NS" port-forward "svc/$SVC" "$PORT:5432" --address 127.0.0.1
  echo "$(date '+%F %T') port-forward exited; reconnecting in 2s..." >&2
  sleep 2
done
