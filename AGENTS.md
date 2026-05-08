# Agent Operating Notes

This repository contains the Xiaohongshu trend digest service.

## Collaboration Rules

- After every meaningful code or documentation change, run the relevant tests and sync the finished commit to `https://github.com/cym00001-code/xiaohongshu`.
- Do not commit real API keys, SMTP passwords, Xiaohongshu session data, cookies, proxy credentials, or raw exported user datasets.
- Keep data collection behind provider interfaces. Do not add captcha bypass, account pools, proxy evasion, private-message collection, media downloaders, or other platform-circumvention code.
- Prefer small, reviewable commits with clear messages.
- Use `main` as the default branch.

## Architecture Preferences

- Keep provider-specific response shapes inside `src/xhs_digest/providers/`.
- Keep orchestration in `src/xhs_digest/digest.py` and avoid putting business logic in the CLI.
- Use `tags.yaml` for topic/tag configuration and `settings.yaml` for runtime behavior.
- The public CLI entrypoint is `daily-digest`.

