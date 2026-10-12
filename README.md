# hyprn-platform

The company's cloud platform, able to host HYPRN MVP and later products: Terraform, staging and prod environments, cloud identities and access, governance and repository protections, the fixed deployment contract, the host reconciler, policies and runbooks. **No product code** — the product lives in [`../hyprn-mvp`](../hyprn-mvp).

Ownership: the product owns scientific and API contracts, data schema migrations, health behaviour and images; the platform owns allowed deployment classes, cloud bindings, trust policy, host templates and the desired release per environment. Terraform owns cloud resources; the reconciler owns rendered runtime state; neither rewrites the other's artifacts.

Status: skeleton. Implementation starts with the cloud work, after the local edition. The platform specification will live in `docs/specs/`.

```
bootstrap/ governance/ contracts/v1/ conventions/
infra/modules/{environment,host}/  infra/environments/{staging,prod}/
environments/{staging,prod}/       host/ policies/ tests/ catalog/ runbooks/
docs/{specs,adr}/        .github/workflows/ (later)
```
