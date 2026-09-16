# Configuration layer

This directory is reserved for committed, non-secret control-plane configuration such as project-profile references, policy references, tool-profile declarations, and model-provider configuration templates.

Rules:
- secrets and tokens must never be committed here;
- machine-specific paths belong in local overrides or generated project profiles when practical;
- project-specific authoritative policy remains in the project repository or an explicitly referenced policy file;
- configuration must not bypass Supervisor validation or approval boundaries.

Gate 002 defines only the configuration boundary. Runtime configuration loading is implemented in later Gates.
