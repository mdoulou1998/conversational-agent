# CLAUDE.md

Context and conventions for this repo. Read this before any change.

## 1. What this is

A starter scaffold for a **conversational support agent for a SaaS product**. A customer
sends a message; the agent resolves the issue, takes an action, or escalates to a human.

This repo is an interview artifact. It will be walked through live, on a shared screen, by
engineers who will ask *why this structure* and *what would you change*. Optimise for a
reviewer reading the code cold, not for feature count.

**What that means in practice:**

- Two or three layers that actually work beat five half-built ones.
- Named abstractions and obvious seams matter more than cleverness.
- Every file should be defensible in one sentence. If it isn't, it shouldn't exist.
- No AI slop: no speculative abstraction, no dead config, no commented-out code, no
  docstrings that restate the function name, no defensive `try/except` that swallows.

## 2. Hard constraints

- **Python 3.12.** Standard library first. `pydantic` for schemas, `pytest` for tests.
- **Hand-rolled orchestration. No agent framework.** No LangChain, LlamaIndex, LangGraph,
  CrewAI, AutoGen. The loop is ours and must be readable end to end in one sitting.
- **Model access via the Google Gen AI SDK (`google-genai`)**, behind our own interface —
  SDK types do not leak past `llm/gemini.py`.
- **Everything external is stubbed**: knowledge base, account data, refunds, tickets.
  Stubs return realistic, deterministic fixtures. No vector DB, no HTTP, no database.
- **Build budget is around two days.** Ask before anything that costs more than an hour.
- **No new dependency without asking.** Name the alternative you rejected.

## 3. Architecture

```
├── AI-Native-Conversational-Agent-Candidate-Brief-Multiverse (1).pdf
├── CLAUDE.md
├── README.md
├── docs       # Add any design docs and decisions                 
├── mypy.ini
├── prompts
│   └── system_v1.txt
├── pyproject.toml
├── ruff.toml
├── src
│   ├── support_agent
│   │   ├── __init__.py
│   │   ├── config.py    # settings: model name, caps, budgets. No magic numbers elsewhere.
│   │   ├── domain.py.   # Message, ToolCall, ToolResult, AgentOutcome, StopReason
│   │   ├── eval
│   │   │   ├── cases.py
│   │   │   └── metrics.py
│   │   ├── llm
│   │   │   ├── base.py.    # LLMClient protocol: complete(messages, tools) -> LLMDecision
│   │   │   ├── fake.py     # scripted, deterministic client for tests and evals
│   │   │   └── gemini.py.  # google-genai adapter
│   │   ├── loop.py         # the agent loop: decide -> validate -> execute -> observe
│   │   ├── main.py
│   │   ├── prompts.py
│   │   ├── session.py      # multi-turn conversation state + history assembly
│   │   ├── tools
│   │   │   ├── account_lookup.py.  # Account lookup on customer id
│   │   │   ├── actions.py          # issue_refund, reset_password, create_ticket  
│   │   │   ├── escalate.py         # Escalate to human
│   │   │   ├── fixtures.py         # Dummy customer data
│   │   │   ├── kb_search.py        # Top k chunks lookup
│   │   │   ├── registry.py          name -> Tool; exports JSON schema for the LLM
│   │   │   └── schema.py           # Shapes tool registry schema for llm
│   │   └── validate
│   │       └── validation.py.       # validate a proposed tool call before it executes
│   └── support_agent.egg-info
│       ├── PKG-INFO
│       ├── SOURCES.txt
│       ├── dependency_links.txt
│       ├── requires.txt
│       └── top_level.txt
├── tests
│   ├── test_loop.py
│   └── test_session.py
└── uv.lock
```

**The seams that matter.** These are the three places the panel will poke, so keep them
clean and injectable:

1. `LLMClient` — swap Gemini for a scripted fake without touching the loop.
2. `Tool` / `ToolRegistry` — the loop knows names and schemas, never implementations.
3. `validation` — sits between "the model asked for this" and "we did this". Always.

Construct dependencies at the edge (`main.py` / test fixtures) and pass them in. No module
imports a concrete LLM or tool implementation except the composition root.

## 4. Behaviour the loop must guarantee

- **Termination is explicit, never emergent.** Every run ends with a `StopReason`:
  `resolved`, `escalated`, `step_limit`, `budget_exhausted`, or `policy_block`. Enforce a
  max-step cap, a token/cost budget, and a repeat-call guard (identical tool + args twice
  in a row is a loop, not progress).
- **Multi-turn works.** `Session` holds ordered turns and resolved referents so
  "what about for the second order?" binds correctly. Keep referent resolution visible in
  code, not buried in a prompt.
- **Tool calls are untrusted input.** Order: schema-validate args → coerce → policy check
  → execute → record. Unknown tool name, bad types, or a failed rule is a handled outcome
  that goes back into the loop as an observation, never an exception that kills the run.
- **Destructive actions are gated.** `ToolSpec` marks read-only vs destructive. Destructive
  calls require: the entity exists, it belongs to this `customer_id`, the amount is within
  cap and within the order total, and the action hasn't already been performed
  (idempotency key). A refund the model invented fails closed and escalates.
- **Every step is observable.** One structured event per step: model decision, tool, args,
  validation result, latency, tokens, cost. The eval harness reads these; don't add a
  second reporting path.

## 5. Evaluation

Quality is defined here as: **did the agent reach the correct terminal action without an
unsafe side effect, and at what cost?** Score four things per case:

- `outcome_correct` — right terminal action (resolve / act / escalate).
- `action_safety` — zero unauthorised or out-of-policy destructive calls. Weighted hardest;
  this is the metric that would get a real deployment stopped.
- `escalation_calibration` — escalated when it should, didn't when it shouldn't.
- `efficiency` — steps and token cost to resolution.

Cases run against `FakeLLM` scripts so they're deterministic and free. Include adversarial
cases: prompt injection in a KB chunk, a refund for someone else's order, a
partially-broken tool response, an ambiguous follow-up. Write cases before the feature they
cover where practical.

## 6. How to work with me

- **Plan first.** For anything beyond a one-file change, give me a short plan: files
  touched, the shape of the change, the tradeoff you're making. Wait for a yes.
- **One concern per change.** No drive-by refactors, no reformatting files you're not
  working in, no renaming things I didn't ask you to rename.
- **Say what you skipped.** If you left an edge case, name it rather than papering over it.
- **Push back.** If my instruction makes the design worse, say so before implementing it.
- **Log decisions.** Any non-obvious choice gets one line in `docs/DECISIONS.md`: decision,
  reason, rejected alternative. I need to defend these live.
- **Explain new territory.** I'm strong in Python, cloud and CI/CD, and newer to agent
  orchestration. When the choice is in that second bucket, explain the
  reasoning, not just the code.

## 7. Code conventions

- Type hints everywhere; `mypy --strict` clean. `pydantic` models at boundaries,
  dataclasses internally.
- Functions do one thing and fit on a screen. Prefer pure functions; push I/O to the edges.
- Explicit errors: a small exception hierarchy in `domain.py`. Never catch bare `Exception`.
- Naming carries the design: `validate_tool_call`, `StopReason.policy_block`,
  `ToolSpec.destructive`. A reader should follow the flow from names alone.
- Comments explain *why*. Delete any comment that explains *what*.
- Prompts live in `prompts/` as text files, versioned, loaded by name — not f-strings
  scattered through the loop.
- No `print`. Use `observability.py`.

## 8. Build order (two days)

Ship in this order and stop where time runs out. A working slice beats broad coverage.

1. `domain.py`, `tools/`, `registry`, `FakeLLM`, `loop.py` with termination. End-to-end on
   a stub run.
2. `session.py` multi-turn + follow-up reference test.
3. `policy/validation.py` + tests, including the adversarial refund case.
4. `evals/` harness with 8–12 labelled cases and a printed scorecard.
5. Real Gemini adapter behind a config flag.
6. `docs/DESIGN.md` and `docs/DECISIONS.md` tidied for the walkthrough.

## 9. Out of scope — do not build

Multi-tenancy, auth, a web UI or API layer, real retrieval or embeddings, streaming,
async/concurrency, persistence beyond in-memory, Docker, CI config, retry/backoff
infrastructure, a plugin system for tools.

These are deliberate omissions, noted in `docs/DESIGN.md` as talking points. If you think
one is genuinely needed, ask — don't add it quietly.

## 10. Commands

```bash
uv sync                       # install
uv run pytest -q              # tests
uv run mypy src               # types
uv run ruff check src tests   # lint
uv run python -m support_agent.evals.harness   # scorecard
uv run python -m support_agent.main            # interactive run against stubs
```