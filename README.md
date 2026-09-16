# conversational-agent

## 1. What this is

A scaffold for a conversational support agent for a SaaS product: a customer sends a
message, the agent looks things up, validates and takes an action, or escalates to a
human. It demonstrates a hand-rolled decide -> validate -> execute -> observe loop with
explicit termination, a tool registry the loop never reaches inside, and a validation
layer that sits between "the model asked for this" and "we did this". See `CLAUDE.md`
for the full working agreement and target architecture this scaffold is built against.

## 2. Status at a glance

| Requirement                    | Where it lives                                                  | Status  |
|---------------------------------|------------------------------------------------------------------|---------|
| R1 Agent loop and termination    | `domain.py` (`StopReason`, `AgentOutcome`), `loop.py` (`AgentLoop.run`) | Partial |
| R2 Multi-turn                    | `session.py` (`Session`)                                          | Partial |
| R3 Tool-call validation          | `validate/validation.py` (`validate_tool_call`)                   | Partial |
| R4 Evaluation                    | `eval/cases.py`, `eval/metrics.py`                                | Not built |

- **R1**: five of six `StopReason` values are reachable (see §7); only the happy path
  (`resolved`) has a test. `BUDGET_EXHAUSTED` is defined but dead - nothing counts tokens.
- **R2**: `Session` assembles ordered history correctly and has three passing tests, but
  there is no explicit follow-up-reference resolution ("what about the second order?")
  anywhere in code, and no test for it - this is called for in `CLAUDE.md` §4 and §8 but
  not present.
- **R3**: ownership, refund cap and order-total checks are implemented and correct on
  inspection, but there is no `tests/test_validation.py` - the adversarial cross-customer
  refund case `CLAUDE.md` §8 asks for by name does not exist as a test.
- **R4**: `eval/cases.py` and `eval/metrics.py` are one-line docstrings each, nothing
  else. There is no harness and no scorecard.

## 3. Quickstart

Prerequisites: Python 3.12+ (this checkout's `.venv` runs 3.14.5; `pyproject.toml` pins
`>=3.12`), and `uv`. `uv` was not on the machine this README was written on, so the
commands below were run against the checked-in `.venv` directly - same packages `uv sync`
would install, per `uv.lock`.

```bash
uv sync                       # install (or: use the existing .venv/bin/* directly)
uv run pytest -q              # tests - no API key needed
uv run mypy src                # types - no API key needed
uv run ruff check src tests    # lint - no API key needed
uv run python -m support_agent.main   # one live turn against Gemini - needs GEMINI_API_KEY
```

Only `main.py` needs `GEMINI_API_KEY` (read via `.env`, gitignored). Tests use `FakeLLM`
and the in-memory fixtures in `tools/fixtures.py`, so nothing else touches the network.

Real results from this checkout, via `.venv/bin/...`:

- `pytest -q` - **4 passed** (1 in `test_loop.py`, 3 in `test_session.py`).
- `mypy src` - **7 errors** in `tools/escalate.py`, `tools/account_lookup.py`,
  `tools/actions.py`, `tools/registry.py` (missing return/generic annotations, plus two
  argument-type mismatches from the loosely-typed tool schema dicts). `CLAUDE.md`'s
  "mypy --strict clean" is not currently true.
- `ruff check src tests` - **9 errors**, all `E501` (docstrings over the 100-char limit
  in `domain.py`, `session.py`, `tools/account_lookup.py`, `tools/actions.py`).
- `python -m support_agent.evals.harness` (the scorecard command in `CLAUDE.md` §10) -
  does not run: the package is `eval`, not `evals`, and no `harness.py` exists.

## 4. Architecture

```
src/support_agent/
  __init__.py          # empty; package marker only
  config.py            # step cap, refund cap, Gemini model name, system prompt name
  domain.py            # Message, ToolCall, ToolResult, ValidationResult, AgentOutcome, StopReason
  session.py           # Session: ordered history, customer_id, step/token budget, repeat guard
  loop.py              # AgentLoop: decide -> validate -> execute -> observe, with termination
  main.py              # composition root: wires GeminiClient + ToolRegistry + AgentLoop
  prompts.py           # load_prompt(name): reads prompts/<name>.txt
  llm/
    base.py            # LLMClient Protocol, LLMDecision
    fake.py            # FakeLLM: scripted deterministic client for tests
    gemini.py          # GeminiClient: google-genai adapter; no SDK types leave this module
  tools/
    schema.py          # {name, description, parameters} schemas handed to the LLM
    registry.py        # Tool protocol, FunctionTool, TOOLS dict, ToolRegistry
    account_lookup.py  # account_lookup(customer_id) stub
    kb_search.py        # kb_search(query, top_k) stub
    actions.py           # issue_refund, reset_password, create_support_ticket stubs
    escalate.py          # escalate_case(customer_id, reason) stub
    fixtures.py           # deterministic Customer/Order/KBChunk fixture data
  validate/
    validation.py        # validate_tool_call: schema check, then per-tool destructive checks
  eval/
    cases.py              # empty - labelled scenarios not yet written
    metrics.py            # empty - scoring functions not yet written
prompts/
  system_v1.txt           # versioned system prompt, loaded by name
tests/
  test_loop.py             # one end-to-end happy-path test (reset_password -> resolved)
  test_session.py          # message/customer_id validation for Session
```

One customer message through `AgentLoop.run` (`loop.py`):

1. `_seed_identity(session)` - on the first turn only, injects a tool message stating the
   authenticated `customer_id`, so the model has a real identity to act against instead of
   trusting free text.
2. `session.add_user_message(user_message)`.
3. Loop, up to `session.max_steps` times:
   1. `self.llm.complete(session.messages, self.registry.schema())` - the model decides.
   2. If it returns no tool call, the message becomes the final answer and the loop
      returns `StopReason.RESOLVED`.
   3. Otherwise, `validate_tool_call(call, session, registry)` schema-checks the call and,
      for destructive tools, runs ownership/cap/total checks. A failure returns
      `StopReason.POLICY_BLOCK` without executing anything.
   4. `_is_repeat` checks the call's `(name, args)` signature against every prior call this
      session. A repeat returns `StopReason.LOOP_DETECTED`.
   5. `self.registry.execute(validated_call)` runs the tool and, if it is marked
      `escalates`, sets `ToolResult.escalated`.
   6. `session.add_tool_result(result)` - the result is serialised as JSON and appended to
      history, so the next `complete()` call sees it.
   7. If `result.escalated`, the loop returns `StopReason.ESCALATED`. Otherwise it repeats
      from step 3.1.
4. If the loop exhausts `session.max_steps` without resolving, it returns
   `StopReason.STEP_LIMIT`.

## 5. Key seams

- **`LLMClient`** (`llm/base.py`): a `Protocol` with one method, `complete(messages,
  tools) -> LLMDecision`. `llm/fake.py`'s `FakeLLM` plays back a fixed list of
  `LLMDecision`s for tests; `llm/gemini.py`'s `GeminiClient` calls the real API and
  translates the response back. To swap providers, write a new class with the same
  `complete` signature and pass it to `AgentLoop(llm=...)` - nothing else changes.
- **`Tool` / `ToolRegistry`** (`tools/registry.py`): `Tool` is a `Protocol`
  (`name`, `description`, `destructive`, `escalates`, `parameters`, `invoke`);
  `FunctionTool` adapts a plain stub function to it. To add a tool, write the stub
  function, add its schema to `tools/schema.py`, and add one entry to the `TOOLS` dict -
  the loop only ever sees names and schemas via `ToolRegistry.schema()`.
- **`validate_tool_call`** (`validate/validation.py`): runs before every execution -
  schema/required-args check for all tools, then (only for `destructive` tools) a
  per-tool branch (`_validate_refund`, `_validate_reset_password`). To gate a new
  destructive tool, add another `if call.name == "...":` branch here.

## 6. Safety of actions

Enforced today, in `validate/validation.py`:

- Every tool call is checked for missing required arguments before anything runs.
- `issue_refund`: the order must exist, `order.customer_id` must equal
  `session.customer_id`, the amount must be a positive number, must not exceed the order
  total, and must not exceed `config.REFUND_CAP` (50.0).
- `reset_password`: the `customer_id` argument must equal `session.customer_id`.

Known gaps, stated plainly:

- **No idempotency key.** Nothing stops the model from issuing two valid-looking refunds
  against the same order with two different amounts - `CLAUDE.md` §4 calls for an
  idempotency key on destructive actions; none exists.
- **The repeat-call guard is stricter than specified.** `_is_repeat` in `loop.py` checks
  a call's signature against *every* prior call in the session, not just the immediately
  preceding one, even though `CLAUDE.md` §4 describes "identical tool call and args twice
  in a row". As written, a legitimate second identical lookup later in a long
  conversation would incorrectly end the run as `LOOP_DETECTED`.
- **`escalate_case` and `create_support_ticket` take a `customer_id` argument that is
  never checked against `session.customer_id`.** Only `destructive` tools reach the
  ownership branch in `validate_tool_call`; these two are marked non-destructive, so a
  model could pass any customer's ID here unchecked.
- **No defence against prompt injection in tool output.** `kb_search` returns raw chunk
  text straight into the next model call with no sanitisation or provenance marking.

## 7. Termination

`StopReason` (`domain.py`): `resolved`, `escalated`, `step_limit`, `budget_exhausted`,
`policy_block`, `loop_detected`.

Reachable in the current loop: `resolved`, `escalated`, `step_limit`, `policy_block`,
`loop_detected` - confirmed by reading every `return AgentOutcome(...)` in `loop.py`.
**`budget_exhausted` is not reachable**: `Session.token_budget` and
`AgentOutcome.token_usage` exist as fields but nothing in `loop.py` ever reads or
increments them.

## 8. Evaluation

`CLAUDE.md` §5 defines quality as four scored dimensions: `outcome_correct` (right
terminal action), `action_safety` (zero unauthorised destructive calls, weighted
hardest), `escalation_calibration`, and `efficiency` (steps and token cost).

**Not built yet.** `eval/cases.py` and `eval/metrics.py` each contain a single module
docstring and nothing else - no labelled cases, no scoring functions, no harness, no
scorecard.

## 9. How this was built with AI

`CLAUDE.md` is the steering contract used throughout: it fixes the hard constraints (no
agent framework, hand-rolled loop, everything external stubbed, Gemini behind
`llm/gemini.py` only), names the three seams that had to stay clean (`LLMClient`,
`Tool`/`ToolRegistry`, `validate_tool_call`), and sets the working agreement - plan
first, one concern per change, say what was skipped. See `CLAUDE.md` directly rather
than a paraphrase here.

Prompts are versioned text files loaded by name (`prompts.py:load_prompt`), not
f-strings inline in the loop - currently one version, `prompts/system_v1.txt`.

Commits are small and single-purpose (`git log --oneline`), e.g. "Move session in to
separate file. For clarity", "Fix mypy.ini and remove dotenv for python dotenv". This
was not uniformly test-driven: `test_loop.py` and `test_session.py` cover the loop's
happy path and `Session` basics, but some later commits (e.g. wiring up
`StopReason.ESCALATED`) changed runtime behaviour without a new test landing alongside.

## 10. Deliberate omissions

Per `CLAUDE.md` §9:

- **Multi-tenancy, auth, a web UI or API layer** - out of scope because the brief is the
  agent's reasoning core, not its deployment surface.
- **Real retrieval/embeddings, persistence beyond in-memory** - the two-day budget goes
  to the loop, validation, and eval seams; deterministic stubs are sufficient to exercise
  and score them.
- **Streaming, async/concurrency** - would add complexity to the loop without changing
  the properties under review (termination, validation, safety).
- **Docker, CI config, retry/backoff infrastructure** - operational concerns, not agent
  design; the brief scores design decisions, not deployment readiness.
- **A plugin system for tools** - the registry is a flat, readable dict on purpose; a
  plugin system would be speculative abstraction ahead of any actual need, which
  `CLAUDE.md` §1 rules out directly.

## 11. Known issues and next steps

1. Add `tests/test_validation.py` with the adversarial cross-customer refund case -
   currently the single largest gap against `CLAUDE.md`'s own build order.
2. Fix `_is_repeat` in `loop.py` to compare only against the immediately preceding call,
   matching the "twice in a row" rule it's meant to implement.
3. Add an idempotency key to destructive tool calls.
4. Build `eval/harness.py` plus 8-12 labelled cases per `CLAUDE.md` §8 step 4.
5. Check `customer_id` on `escalate_case` and `create_support_ticket` against
   `session.customer_id`, the same way destructive tools already do.
6. Wire step/token counting into `loop.py` so `BUDGET_EXHAUSTED` is reachable and
   `AgentOutcome.token_usage` reflects real usage.
7. Fix the 7 `mypy --strict` errors and 9 `ruff` `E501`s so those CLAUDE.md claims hold.
8. Write `docs/DESIGN.md` and `docs/DECISIONS.md` - `docs/` currently exists but is empty.

## 12. Why Python

The build budget was two days and Python is my strongest language, so it was the fastest
path to a correct, readable loop rather than a learning exercise. The seams that matter
here - `Protocol`-based `LLMClient`, a name-and-schema-only `ToolRegistry`, a validation
function sitting between decision and execution - map directly onto TypeScript
interfaces and a discriminated-union result type, so the design choices carry over even
though the code doesn't.
