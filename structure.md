eldercare-platform/
├─ apps/
│  ├─ web/                               # Next.js frontend
│  ├─ api/                               # FastAPI backend
│  ├─ worker/                            # Celery workers
│  └─ scheduler/                         # Celery beat / scheduled jobs
├─ libs/
│  ├─ contracts/                         # shared DTO/event schemas (OpenAPI/JSONSchema)
│  ├─ events/                            # event definitions + routing keys
│  ├─ authz-policy/                      # reusable consent/RBAC policy primitives
│  ├─ notifications-sdk/                 # shared notification clients
│  └─ observability/                     # logging/tracing/metrics helpers
├─ infra/
│  ├─ docker/
│  │  ├─ api.Dockerfile
│  │  ├─ web.Dockerfile
│  │  ├─ worker.Dockerfile
│  │  ├─ scheduler.Dockerfile
│  │  └─ nginx.Dockerfile
│  ├─ compose/
│  │  ├─ docker-compose.dev.yml
│  │  ├─ docker-compose.staging.yml
│  │  └─ docker-compose.prod.yml
│  ├─ k8s/                               # optional future extraction target
│  │  ├─ base/
│  │  └─ overlays/
│  ├─ terraform/
│  │  ├─ modules/
│  │  │  ├─ network/
│  │  │  ├─ postgres/
│  │  │  ├─ redis/
│  │  │  ├─ object-storage/
│  │  │  ├─ secrets/
│  │  │  └─ monitoring/
│  │  └─ envs/
│  │     ├─ dev/
│  │     ├─ staging/
│  │     └─ prod/
│  ├─ nginx/
│  │  ├─ nginx.conf
│  │  └─ conf.d/
│  └─ scripts/
│     ├─ bootstrap.sh
│     ├─ migrate.sh
│     ├─ seed.sh
│     └─ smoke-test.sh
├─ docs/
│  ├─ architecture/
│  ├─ api/
│  ├─ security/
│  ├─ runbooks/
│  └─ adr/
├─ tools/
│  ├─ ci/
│  └─ codegen/
├─ .github/
│  └─ workflows/
├─ .env.example
├─ Makefile
├─ README.md
└─ LICENSE