# hyprn-platform — agent instructions

- Infrastructure and operations only. Product code belongs in `../hyprn-mvp`.
- Never commit credentials, Terraform state or plan files, tfvars with secrets, or downloaded service-account keys.
- Never apply infrastructure changes or create cloud resources without explicit owner authorization for that exact plan. Plans are reviewed before apply; staging and prod have separate authority.
- Read the platform specification in `docs/specs/` before implementing anything; record decisions in `docs/adr/`.
