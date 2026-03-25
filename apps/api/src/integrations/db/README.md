# Database Integration Layout

This directory contains baseline PostgreSQL migration assets for the eldercare platform.

## Structure
- migrations/versions: versioned schema DDL
- migrations/seeds: non-PHI seed data for bootstrapping local and staging environments
- policies/consent_filters.sql: consent-aware helper functions
- policies/row_level_security.sql: RLS policies that rely on app.current_user_id setting
- readmodels: analytics rollup documentation and assets

## Execution
Run migration pipeline:

PowerShell:
- ./infra/scripts/db/migrate.ps1

Run migration smoke tests:

PowerShell:
- ./infra/scripts/db/smoke-test.ps1

## Application-side RLS context
Before reading protected tables from API code, set session setting per connection:
- SET app.current_user_id = '<actor-uuid>';
