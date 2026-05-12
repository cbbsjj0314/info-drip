# AGENTS.md

## Purpose

Repository-level instructions for coding agents working on InfoDrip.

Keep this file short. Put detailed repeatable procedures in `docs/runbook/`.

## Project Context

### Project Identity

InfoDrip is a personal iPad PDF learning assistant.

It helps the user read PDF documents, select passages, request LLM explanations, extract glossary terms, generate quizzes, track quiz attempts, and replay review-again quiz attempts.

The project is not a generic PDF chatbot. It is a selected-text based learning workflow app that stores study activity as structured data.

### Repository

- Repository: `cbbsjj0314/info-drip`
- Primary MVP client: iPad native app
- Future client: Android native app
- Backend: FastAPI
- MVP database: SQLite

### Current MVP Direction

The MVP is a local-first iPad + backend system:

- iPad app built with SwiftUI and PDFKit
- FastAPI backend
- SQLite database
- Backend-stored uploaded PDF files
- Backend-extracted page text
- Selected-text based LLM workflows
- OpenAI-compatible LLM provider interface
- JSON output validation before persistence
- LLM request logging for model, token usage, latency, status, and estimated cost

### Core Learning Flow

InfoDrip MVP focuses on this flow:

    PDF upload
    → PDF reading
    → text selection
    → highlight persistence
    → LLM explanation
    → glossary extraction
    → question answering
    → quiz generation
    → quiz attempt tracking
    → review-again tracking
    → review-again replay
    → document-level study record lookup

`review_cards` exists as backend/API capability, but separate review card UX is deferred and not the primary MVP review flow.

## Non-goals

InfoDrip MVP is not:

- a generic PDF chatbot
- a public SaaS product
- a multi-user learning platform
- an OCR system
- a full RAG system
- a vector database project
- a complex spaced repetition engine
- a ChatGPT web/app automation wrapper
- a payment or subscription product
- a real-time collaboration tool
- an Apple Pencil handwriting recognition app
- a separate review card list/detail/edit/delete UX

## Core Boundary

- The iPad app must not store LLM API keys.
- LLM API keys must be stored only in backend environment variables.
- The iPad app calls only the backend API.
- The backend calls the LLM provider.
- Do not send the full PDF text to the LLM for every request.
- Use selected text and necessary surrounding context for LLM tasks.
- PDF files may be uploaded to and stored by the backend in the MVP.
- Page text may be extracted and stored by the backend.
- LLM responses should use JSON outputs where practical.
- Validate LLM outputs before storing them.
- Store user learning records in the database.
- Log LLM provider, model, token usage, latency, status, and estimated cost for each LLM request.
- Treat OCR, RAG, LLM streaming, account systems, payment, and public deployment as out of MVP unless explicitly requested.

## MVP Data Boundary

The database exists to persist study records, not to create a large analytics platform.

MVP persistence should focus on:

- documents
- document_pages
- highlights
- llm_explanations
- glossary_terms
- user_questions
- quizzes
- quiz_attempts
- review_cards
- llm_request_logs

Primary review UX should center on `quiz_attempts` and review-again listing/replay. Treat `review_cards` as deferred backend/API capability unless explicitly requested.

Avoid adding broad analytics, dashboards, recommendation engines, or complex review scheduling unless explicitly requested.

## LLM Boundary

LLM features are task-specific, not one generic chat layer.

Expected LLM tasks:

- explanation generation
- glossary extraction
- question answering
- quiz generation
- optional/deferred: review card generation
- later: weakness analysis

Rules:

- Keep prompt inputs explicit.
- Separate selected text from surrounding context.
- Prefer structured JSON outputs.
- Validate response structure with Pydantic or equivalent schemas.
- Store raw response only when useful for debugging or audit.
- Do not treat LLM output as inherently trusted.
- Do not expose API keys, provider account details, or private runtime data.

## Working Rules

- Before changing files, state a short plan and relevant assumptions.
- Prefer the smallest useful slice that satisfies the task.
- Do not add speculative abstractions, broad configurability, or future platform behavior.
- Touch only files required by the current task.
- Do not reformat, rename, or refactor unrelated code.
- Ask for clarification when task boundary, data contract, runtime boundary, or security boundary is ambiguous.
- Prefer repo-grounded evidence from code, tests, docs, and `docs/local/NEXT.md` when available.
- Do not create branches, commits, pull requests, issues, or labels unless the user explicitly asks.
- Do not perform git operations unless the user explicitly asks.
- Do not edit files through remote tools unless the user explicitly asks.

## Code Comments

- Prefer clear names, small functions, and explicit schemas over comments.
- Add comments only for non-obvious intent, invariants, security boundaries, LLM/data trust boundaries, or deliberate tradeoffs.
- Do not add comments that merely restate what the code does.
- Keep code comments in English by default so they fit code-facing identifiers and tool output.
- Write TODO comments only when they include the concrete future condition, blocker, or decision needed.

## Default Scope

Keep the MVP local-first.

Default implementation assumptions:

- Backend uses Python, FastAPI, Pydantic, SQLite, pytest, and ruff.
- Backend package/dependency management uses `uv` unless changed by the user.
- First iPad client uses Swift, SwiftUI, and PDFKit.
- Android is a later separate client that reuses the backend API.
- PDF storage uses backend upload/storage for MVP.
- LLM provider should be OpenAI-compatible and configurable through environment variables.
- Quiz types for MVP are `short_answer` and `fill_blank`.

Do not add these unless explicitly requested:

- OCR
- RAG
- vector DB
- LLM streaming
- user account system
- payment
- public deployment
- complex spaced repetition
- Android implementation
- Apple Pencil handwriting recognition
- full PDF annotation editor

## Suggested Project Structure

Use this direction unless the user changes it.

    backend/
      app/
      tests/
      pyproject.toml
      README.md
      .env.example

    ios/
      InfoDrip/

    docs/
      runbook/
      planning/

    docs/local/
      NEXT.md
      WORKING_RULES.md
      checkpoints/

`docs/local/` is local-only working material and should be ignored by Git.

## Documentation Boundary

- Write durable human-facing docs in Korean by default.
- Agent-facing instruction files may use English when useful for tool compatibility.
- Do not translate code-facing identifiers such as `endpoint`, `route`, `table`, `model`, `schema`, `view`, `API`, `CLI`, command names, module names, class names, function names, config keys, or filenames.
- Keep `docs/local/` as local-only working material, not a public changelog.
- `docs/local/NEXT.md` is a local execution board. Keep it short and do not turn it into a detailed progress log.
- If `Done` in `docs/local/NEXT.md` grows too long, move older items into `docs/local/checkpoints/`.
- Do not put secrets, raw private PDF content, private/local paths, provider account details, API keys, tokens, or private runtime data in public docs, prompts, logs, screenshots, fixtures, or reports.
- Use sanitized examples in public docs.

## Local Working Board

`docs/local/NEXT.md` is the local execution board.

Recommended sections:

- Now
- Next
- Later
- Blockers
- Decisions
- Done

Use it to track the current slice. Do not turn it into a permanent changelog.

When one slice is complete, move useful Done items into a checkpoint under:

    docs/local/checkpoints/

Use names like:

    0001-repository-bootstrap.md
    0002-backend-skeleton.md
    0003-document-upload-api.md

## Validation

Backend uses `uv`.

For backend runtime/code changes, run:

- `uv run ruff check .`
- `uv run pytest`

For backend API behavior changes, also run the relevant narrow smoke check when available.

For iPad changes, use the available Xcode build/test validation. If Xcode validation cannot run in the current environment, state that clearly and describe what was checked instead.

For docs-only changes, runtime validation may be skipped. Instead, reread the changed docs and check for:

- outdated claims
- duplicated guidance
- overbroad scope promises
- accidental exposure of secrets or private data
- mismatch with MVP boundaries

If validation cannot run, report:

- command attempted
- failure reason
- what was still verified

## Reporting After Changes

After making changes, summarize:

- files changed
- what was implemented
- validation result
- what was explicitly deferred
- risks, notes, or user confirmation needed

For security-related changes, also summarize:

- what was exposed or potentially exposed
- what was rotated or revoked
- what remains deferred

Keep reports short and concrete.

## Git Conventions

Only when the user explicitly asks for git actions:

- Prefer one branch per current work item.
- Use commit subjects like `type(scope): summary`.
- Suggested types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`.

Examples:

- `chore(repo): bootstrap project structure`
- `docs(planning): add MVP project brief`
- `feat(api): add document upload endpoint`
- `test(api): cover highlight creation`
