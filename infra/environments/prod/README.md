# infra/environments/prod

Terraform root for prod, with its own backend, state and authority, separate from staging. It instantiates [`infra/modules/environment`](../../modules/environment/README.md) and [`infra/modules/host`](../../modules/host/README.md).
