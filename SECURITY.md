# Security Policy

## Supported versions

Only the latest released version receives security fixes.

## Reporting a vulnerability

codecaliper parses arbitrary, potentially untrusted source code through native
tree-sitter grammars, so parser-reachable memory-safety issues are in scope.

Please report vulnerabilities privately. Do not open a public issue.

- preferred: [GitHub private vulnerability reporting](https://github.com/KurathSec/codecaliper/security/advisories/new)
- or by email: kurathandrew@gmail.com

You will receive an acknowledgement within a few days. Please include a
minimal reproducing input and the output of `codecaliper env` (grammar and
binding versions matter for parser issues).

Vulnerabilities in the tree-sitter runtime or grammar crates themselves should
also be reported upstream; we will coordinate the calibrated-pin bump here.
