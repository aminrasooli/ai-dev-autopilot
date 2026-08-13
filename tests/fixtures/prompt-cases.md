# Permission-prompt cases

The catalogue of permission-prompt shapes the approval broker is designed
around. Each case describes a category of request, why a naive permission layer
raises a dialog for it, what the correct handling is, and what an unattended run
should do.

These are generic scenarios, not a log. They exist so that a change to
`hooks/permission-broker.sh` can be argued against a fixed set of shapes rather
than against whichever command happened to prompt most recently. `CASE-01`
through `CASE-06` are asserted in `tests/approval.test.sh` §4; `CASE-07` through
`CASE-09` are design constraints rather than assertions.

Nothing in this file grants permission. It is a decision table.

Format: what is intended · why it prompts · the correct handling · what
unattended mode should do.

---

## CASE-01 — a compound shell probe of a CLI

**Intended:** `some-cli --version; which some-cli; some-cli --help | head -120`

**Why it prompts:** three commands joined with `;` in one invocation. A compound
command cannot be matched against an allowlist entry as a unit, so the whole
line is unclassified.

**Correct handling:** decompose into single-purpose invocations, each of which
is a read-only introspection call, and allow those. The rule is a property of
the *shape* of the command, not of its content.

**Unattended:** allow, but only in the decomposed form. An unattended run should
refuse compound command lines outright and require one operation per call. That
keeps every executed command individually reviewable in the transcript, which is
what makes an unattended run auditable afterwards.

## CASE-02 — `cat` / `ls` used as a file reader

**Intended:** `cat ~/notes.txt`, `ls -la <project>`

**Why it prompts:** reading files through a shell when a dedicated, sandboxed
read tool exists. The shell path is broader than the operation needs and is not
subject to the same tool-level path checks.

**Correct handling:** use the `Read` and `Glob` tools.

**Unattended:** never allow the shell form. This is not a permission question,
it is a tool-selection defect. Unattended mode should treat `cat`/`ls`/`head`/
`tail`/`sed` against a plain path as a hard error and force the dedicated tool,
because the dedicated tool is the surface the credential denies are attached to.

## CASE-03 — build a fixture tree by executing a generated script

**Intended:** `chmod +x make-fixtures.sh; ./make-fixtures.sh <dir>; find <dir> -type f`

**Why it prompts:** it makes a file executable and then runs it. "Write a
script, then execute the script you just wrote" is exactly the shape of the
attack this framework exists to stop, so it should prompt.

**Correct handling:** the `Write` tool, one call per fixture file. A contract
test may still create its fixture tree at runtime, but from a reviewed file in
the repository rather than one synthesised during the session.

**Unattended:** never allow the general form. Executing a file written earlier in
the same session must stay human-gated. Allow only the narrow case of running a
script that is *already tracked in git at the committed revision* — that is a
reviewed artifact, and it covers the real need, which is running
`tests/*.test.sh`.

## CASE-04 — a local commit

**Intended:** `git add -A && git commit -m ...`

**Why it prompts:** it does not — commit is allowed; `git push` is the gated
operation. Recorded to fix the boundary in writing, because the two are
routinely confused.

**Unattended:** allow `commit` on a non-default branch. Continue to block
`push`, `reset --hard`, `clean -fd` and history rewriting with no exception;
there is no unattended benefit that outweighs an unsupervised force-push.

## CASE-05 — a sync that writes user settings and needs privilege

**Intended:** `make -C <hub> sync`, which rewrites `~/.claude/settings.json` and,
for the managed floor, writes under `/etc/claude-code/` via `sudo`.

**Why it prompts:** `sudo` is human-gated by `core/security.md`, and
`~/.claude/settings.json` is a protected settings file the sandbox always
refuses.

**Correct handling:** none — this one is genuinely gated. The user-scope half of
the sync is reported to the human as a required follow-up step rather than
attempted.

**Unattended:** never allow. A run that can rewrite its own enforcement floor
while unsupervised has no enforcement floor. Unattended mode should detect that a
sync is *needed* and report it, never perform it.

## CASE-06 — writing fixture files under the session scratchpad

**Intended:** `Write` of several fixture files under the session scratchpad
directory, which the harness advertises as isolated from the user's project and
usable without permission prompts.

**Why it prompts:** it should not. The sandbox policy lists the scratchpad and
`$TMPDIR` as write-allowed. A prompt here is a false positive on an operation
that is reversible, confined and explicitly pre-authorized.

**Correct handling:** allow. Where a fixture tree is durable rather than
throwaway, keeping it in the repository is better anyway — the payload is
reviewable in git rather than synthesised per session.

**Unattended:** allow. An unattended run that cannot write to its own scratchpad
will either stall or start putting temporary state somewhere worse. A batch of
same-shaped writes should be classified once, not once per file.

## CASE-07 — the out-of-sandbox probe cannot run from inside a session

**Intended:** `bin/host-check`, the authoritative out-of-sandbox probe.

**Why it fails:** it refuses with "running INSIDE Claude's sandbox — results
would be invalid" whenever `sandbox.excludedCommands` does not actually escape
the sandbox for that invocation. Whether it does is a property of how the
session was started.

**Correct handling:** none. The check is deliberately unfakeable, and producing
a fake result would be worse than producing none. Report it as not-run, never as
passed.

**Unattended:** this is the load-bearing question for unattended mode.
`host-check` is the only probe that verifies the sandbox from outside it; a run
that cannot execute it cannot confirm its own containment. Unattended mode should
run `host-check` from the launching shell *before* handing control to the agent,
and refuse to start if it does not pass.

## CASE-08 — a quoted separator inside an argument

**Intended:** `bash tests/approval.test.sh 2>&1 | grep -E 'FAIL|passed'`

**Why it prompts:** a naive clause splitter treats the `|` inside the quoted
regex alternation as a shell pipeline, producing clauses that are not
recognisable commands. Unrecognised means escalate, so the line escalates while
the broker is working exactly as designed and reaching the wrong conclusion.

**Correct handling:** a quote-aware splitter that masks separators inside quoted
spans and escalates on an unbalanced quote — an unbalanced quote must never merge
a dangerous clause into a benign one. Do **not** fix this by adding a broad
permission rule; that trades a usability defect for a security one.

**Unattended:** allow once the splitter is quote-aware. Until then the escalation
is the safe failure.

## CASE-09 — the hooks directory is read-only to the session that uses it

**Intended:** `chmod +x hooks/<hook>.sh`, or removing a superseded hook.

**Why it fails:** not a prompt — a hard `Read-only file system`. Claude Code
mounts the hooks directory read-only inside a session, so a session can neither
make a hook it just wrote executable nor delete one it superseded. `bin/` is
writable; `hooks/` is not.

**Correct handling:** invoke hooks as `bash <path>` in the settings fragment, so
function does not depend on the executable bit, and put any `chmod` or cleanup in
`bin/activate-approval-broker`, which runs from a normal shell where the
directory is writable.

**Unattended:** this is correct vendor behaviour and should not be worked
around — a session that can rewrite its own hooks has no hooks. Any change to a
hook's mode or existence belongs in the activation script.
