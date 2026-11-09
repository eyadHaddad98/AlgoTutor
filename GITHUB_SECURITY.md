# GitHub publishing checklist

- Commit only the **source code** from this public edition.
- Keep `.env`, API keys, passwords, private keys, local databases, logs and caches off GitHub.
- Do not upload the original 11 course lecture PDFs or extracted records without permission from the copyright holder; both `/data/lectures/` and `/data/processed/` are ignored.
- Run `python scripts/setup.py` locally to create fresh passwords and session secrets. Put the Anthropic key **only** in your local `.env`.
- If a real API key was ever pushed to a public or shared repository, revoke/rotate it in the provider console. Removing it from the latest commit is not enough because Git history persists.
- Before pushing, check `git status` and `git diff --cached --name-only`, and consider a secret scanner such as Gitleaks.
- Your `.env.example` is deliberately made from placeholders only; do not replace them with real credentials.
- The project has not been proven production-ready simply by removing secrets. Review authentication and deployment settings before publicly hosting a live server.
