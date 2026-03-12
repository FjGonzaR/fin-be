# Claude Code Rules — fin-be

## Swagger / OpenAPI

**Whenever an API endpoint is added or modified, `openapi.yaml` must be updated in the same change.**

This includes:
- Response schema changes (fields added, removed, renamed, or retyped)
- New query parameters or changes to existing ones
- Changes to endpoint description / behavior
- New or modified shared schemas (`components/schemas`) such as enums
- New endpoints (add the full path entry under `paths:`)

The file is at `openapi.yaml` in the project root.
