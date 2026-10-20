# Access module

The staging Access boundary admits exact named email addresses through one email
PIN identity provider and one allow policy. The application covers the complete
staging hostname. The connector routes that hostname to loopback and rejects
other requests with 404. DNS publication depends on the completed boundary.

The module exposes nonsecret runtime binding metadata and sensitive evaluated
resource values for policy review. It has no credential inputs or token lookups.
