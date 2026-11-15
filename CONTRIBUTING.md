# Contributing to Smarter Health AI

Thanks for your interest in improving Smarter Health AI! This guide covers how to propose changes, what we expect in a pull request, and a few rules that matter for a health-related project.

## Ground rules

- **`main` is protected.** Nobody pushes to `main` directly. Every change arrives as a **pull request from a separate branch** and is merged after a maintainer approves it.
- **No real patient data, ever.** Don't put real health information, real patient conversations or real medical images in code, tests, issues, screenshots or PRs.
- **No real doctor data.** Doctor records in this repo must be **fictional**. See `backend/scripts/generate_sample_doctors.py`.
- **No secrets.** Never commit `.env` files, passwords, API keys or tokens. Only `.env.example` files with placeholder values belong in git.
- Be respectful and constructive in issues and reviews.

## How to contribute

### 1. Find or open an issue
- **Bug:** open an issue with steps to reproduce, what you expected, what happened, and your OS and versions. Include `curl http://localhost:8000/api/health` output if it's relevant.
- **Feature:** open an issue first to discuss the idea before you write a lot of code.
- Small fixes, such as typos, docs or obvious bugs, can go straight to a PR.

### 2. Fork and create a branch
```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/smarter-health-ai.git
cd smarter-health-ai
git remote add upstream https://github.com/umeshnamdev234/smarter-health-ai.git
git checkout -b feat/short-description
```

Name branches by type:

| Prefix | Use for |
|---|---|
| `feat/` | new features |
| `fix/` | bug fixes |
| `docs/` | documentation only |
| `refactor/` | code changes that don't change behavior |
| `test/` | adding or fixing tests |
| `chore/` | tooling, dependencies, config |

Keep your branch up to date:
```bash
git fetch upstream
git rebase upstream/main
```

### 3. Set up the project
Follow the [README](README.md) quick start. In short:
```bash
ollama pull hf.co/unsloth/medgemma-4b-it-GGUF:Q4_K_M && ollama cp hf.co/unsloth/medgemma-4b-it-GGUF:Q4_K_M medgemma
docker compose up -d --build                  # backend + PostgreSQL
cd frontend && cp .env.example .env.local && npm install && npm run dev
```

To run backend tests and tools locally:
```bash
cd backend
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
```

### 4. Make your change
Keep PRs **small and focused**: one feature or fix per PR. Large PRs are hard to review and slow to merge.

### 5. Check your work before opening a PR

**Backend**
```bash
cd backend
.venv/bin/python -m pytest -q        # all tests must pass
```

**Frontend**
```bash
cd frontend
npx tsc --noEmit                     # no type errors
npm run lint                         # no lint errors
npm run build                        # production build succeeds
```

**Manual check:** run the app and try your change in the browser. For API changes, try them at http://localhost:8000/docs.

### 6. Commit
Write clear commit messages in the imperative mood:
```
fix: show error when doctor database is unreachable
feat: add language filter to doctor suggestions
docs: explain CSV import format
```

### 7. Open the pull request
Push your branch to your fork and open a PR against `main`. In the description, include:
- **What** changed and **why** (link the issue: `Closes #12`).
- **How you tested it**: the commands you ran and the scenarios you tried.
- **Screenshots** for UI changes, in both light and dark theme if relevant.
- Anything reviewers should look at closely.

A maintainer will review it. Please respond to comments by pushing new commits to the same branch. All review conversations must be resolved before merging, and new pushes require re-approval.

## Coding guidelines

### Backend (Python / FastAPI)
- Python 3.11, with type hints on functions.
- Keep model calls in `app/medgemma_client.py`, database queries in `app/db.py`, and prompts in `app/prompts.py`.
- Use Pydantic models (`app/schemas.py`) for request and response validation.
- **Never log message content or images.** They may contain health information. Log metadata only, such as counts and timings.
- Add or update tests in `backend/tests/` for logic changes. Tests shouldn't need a running model or database.

### Database changes (Alembic)
- Change the table definitions in `app/models.py`, then create a migration:
  ```bash
  .venv/bin/alembic revision --autogenerate -m "describe the change"
  ```
- **Review the generated file.** Autogenerate misses triggers and some indexes, so write those by hand.
- **Never edit a migration that is already on `main`.** Add a new one instead.
- Every migration needs a working `downgrade()`.
- Before opening the PR, check that `alembic upgrade head`, `alembic downgrade -1` and `alembic check` all succeed.

### Frontend (Next.js / TypeScript)
- This project uses **Next.js 16**, which has breaking changes from older versions. Check `frontend/node_modules/next/dist/docs/` when unsure.
- Components go in `src/components/`, API calls in `src/lib/api.ts`, and types in `src/lib/types.ts`.
- Style with the CSS variables in `globals.css`. Make sure changes work in **light and dark** themes and at **phone width**.
- Don't render model output as raw HTML. Use the `Markdown` component.

## Changes to medical behavior need extra care

PRs that change how the assistant responds get a closer review. That includes:
- the system or triage prompts (`app/prompts.py`)
- emergency detection (`app/safety.py`)
- specialty triage or doctor ranking (`app/triage.py`, `app/doctors.py`)

For these, please:
- Explain the reason for the change and its expected effect.
- Show before/after examples using **made-up** scenarios.
- Never weaken the emergency warnings or the "not a substitute for professional advice" messaging.
- Add tests where possible, for example new emergency phrases in `safety.py`.

## Reporting security issues

**Don't open a public issue for security vulnerabilities.** Contact the maintainer privately through GitHub (@umeshnamdev234) with details and steps to reproduce. You'll get a response as soon as possible.

## License

By contributing, you agree that your contributions are provided under the same terms as this repository. Use of MedGemma is subject to Google's [Health AI Developer Foundations terms](https://developers.google.com/health-ai-developer-foundations/terms).
