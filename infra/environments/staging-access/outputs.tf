output "binding" {
  value = module.access.binding
}
output "review" {
  value     = module.access.review
  sensitive = true
}
