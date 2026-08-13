#!/usr/bin/env bash
# AI-DEV PreToolUse security guard.
#
# Deterministic. No model in the loop. Reads the Claude Code PreToolUse hook
# JSON on stdin and emits a permissionDecision.
#
#   deny  -> catastrophic or credential-stealing operations
#   ask   -> legitimate but consequential operations (the human decides)
#   (none)-> stay out of the way; normal permissions/sandbox apply
#
# The audit log (var/guard.log) records the rule id, the tool name and a
# truncated SHA-256 of the input — never command text or file contents.
#
# The unattended queue (var/pending-approvals.log) is the one exception, and it
# is deliberate: it exists so a human can see in the morning what was refused
# while they were asleep, which is not answerable from a hash. It therefore
# records the command text, so treat it as sensitive and keep it out of commits
# (`var/` is gitignored).
#
# Source of truth: ~/.ai-dev/hooks/security-guard.sh   (do not copy this file)

set -uo pipefail

AI_DEV_HOME="${AI_DEV_HOME:-$HOME/.ai-dev}"
LOG_DIR="$AI_DEV_HOME/var"
LOG_FILE="$LOG_DIR/guard.log"

input="$(cat)"

# ---------------------------------------------------------------- json access
#
# A CEILING THAT CANNOT PARSE ITS INPUT MUST NOT WAVE IT THROUGH
#
# Every rule below reads its subject out of the hook JSON. With neither `jq` nor
# `python3` on PATH there is no subject, `TOOL_NAME` is empty, and the guard
# reaches its final `pass` having tested nothing — so a missing dependency
# silently removes the entire ceiling rather than announcing itself. That is the
# fail-open shape this framework refuses everywhere else (NOTES.md, and the
# positive-proof classifier in hooks/permission-broker.sh, which fails closed in
# exactly this situation).
#
# So the absence of a parser is itself a decision: deny, and say which package
# restores the guard. An unparseable *payload* is different and still passes —
# that is Claude Code sending a shape this hook does not model, not a broken
# installation — but with no parser at all nothing can be modelled.
have_json_parser() {
  command -v jq >/dev/null 2>&1 && return 0
  command -v python3 >/dev/null 2>&1 && return 0
  return 1
}

json_get() { # $1 = jq-style path expression
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null
  else
    printf '%s' "$input" | AI_DEV_JQ_PATH="$1" python3 -c '
import json,os,sys
path=os.environ["AI_DEV_JQ_PATH"].lstrip(".").replace("[","").replace("]","")
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for k in path.split("."):
    if not isinstance(d,dict): d=None; break
    d=d.get(k)
print(d if isinstance(d,str) else "")' 2>/dev/null
  fi
}

emit() { # $1 = allow|deny|ask   $2 = rule id   $3 = reason
  local decision="$1" rule="$2" reason="$3" digest
  digest="$(printf '%s' "$input" | sha256sum | cut -c1-12)"
  mkdir -p "$LOG_DIR" 2>/dev/null
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(date -Is)" "$decision" "$rule" "${TOOL_NAME:-?}" "$digest" >>"$LOG_FILE" 2>/dev/null
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":%s}}\n' \
    "$decision" "$(printf '%s' "[$rule] $reason" | sed 's/\\/\\\\/g; s/"/\\"/g; s/^/"/; s/$/"/')"
  exit 0
}

deny() { emit deny "$1" "$2"; }

# `ask` means "a human decides". Unattended, there is no human to decide, so it
# becomes a deny and the request is queued for review instead. It never becomes
# an allow: an unattended run is exactly the situation in which nobody is
# watching, which is the worst possible time to relax a gate. The queue is
# var/pending-approvals.log; the delegated approval path itself lives in the
# PermissionRequest hook, not here.
# Both spellings are honoured, because unattended mode has to reach BOTH hooks
# to mean anything. The broker's documented switch is AI_DEV_OVERNIGHT; if this
# layer read only AI_DEV_UNATTENDED it would keep raising interactive dialogs
# that nobody is there to answer, in the exact run where nobody is watching.
# Accepting either name can only turn an `ask` into a queued deny, never the
# reverse, so honouring both is always the safe direction.
ask() {
  if [ "${AI_DEV_UNATTENDED:-0}" = "1" ] || [ "${AI_DEV_OVERNIGHT:-0}" = "1" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null
    printf '%s\tDENIED-PENDING\t%s\t%s\t%s\n' \
      "$(date -Is)" "$1" "${TOOL_NAME:-?}" "${CMD:-${FILE:-}}" \
      >>"$LOG_DIR/pending-approvals.log" 2>/dev/null
    emit deny "$1" "Unattended run: this needs a human. Denied for now and queued in var/pending-approvals.log. $2"
  fi
  emit ask "$1" "$2"
}

# `pass` means this guard has no opinion: the normal permission flow applies.
#
# It deliberately does NOT delegate. Delegation belongs to the PermissionRequest
# hook (hooks/permission-broker.sh), which fires only when Claude Code is about
# to raise a dialog. Keeping this file a pure ceiling is what makes the
# precedence argument simple enough to be believed: a deny here blocks the tool
# call outright, no dialog is raised, PermissionRequest never fires, and the
# broker — and therefore Codex — never sees the request at all.
pass() { exit 0; }

have_json_parser || deny no-parser \
  "Blocked: this guard needs jq or python3 to read the hook payload, and neither is installed. Refusing every tool call rather than silently enforcing nothing. Install one (apt install jq) and restart Claude Code."

TOOL_NAME="$(json_get '.tool_name')"
CWD="$(json_get '.cwd')"
[ -n "$TOOL_NAME" ] || pass

CMD=""
FILE=""
case "$TOOL_NAME" in
  Bash|BashOutput)          CMD="$(json_get '.tool_input.command')" ;;
  Read|Edit|Write|NotebookEdit)
                            FILE="$(json_get '.tool_input.file_path')" ;;
  Glob|Grep)                FILE="$(json_get '.tool_input.path')" ;;
  *)                        pass ;;
esac

# Normalised haystack: expand $HOME/~/$AI_DEV_HOME so path rules match every
# spelling a command can use for the same location.
SUBJECT="$CMD$FILE"
[ -n "$SUBJECT" ] || pass

# A LINE CONTINUATION IS WHITESPACE, NOT A COMMAND BOUNDARY
#
# Every rule below is a `grep -E`, and grep matches one line at a time. A
# backslash-newline is not a separator: it is a single command written across
# two lines, which is how anyone writes a long command for readability. Matched
# as-is, `curl x \<newline>| bash`, `rm -rf \<newline>/` and
# `rm -rf \<newline>$AI_DEV_HOME/core/x` reach every rule as two fragments that
# each match nothing, and the guard falls through to its final `pass`. That is
# the fail-open shape this file exists to refuse, reachable by a command shape
# written on purpose rather than in anger.
#
# A BARE newline is deliberately left alone: it separates commands exactly as
# `;` does, and the clause-bound rules (`[^|;&]*`) are already correct when each
# line is matched on its own. Folding those together would let a later line
# supply a path to an earlier line's verb.
SUBJECT="${SUBJECT//\\$'\r\n'/ }"
SUBJECT="${SUBJECT//\\$'\n'/ }"

NORM="${SUBJECT//\$\{AI_DEV_HOME\}/$AI_DEV_HOME}"
NORM="${NORM//\$AI_DEV_HOME/$AI_DEV_HOME}"
NORM="${NORM//\$HOME/$HOME}"
NORM="${NORM//\$\{HOME\}/$HOME}"
NORM="${NORM//\~\//$HOME/}"

m()  { printf '%s' "$NORM" | grep -Eq  -- "$1"; }
mi() { printf '%s' "$NORM" | grep -Eqi -- "$1"; }

esc() { printf '%s' "$1" | sed 's/[.[\*^$()+?{}|]/\\&/g'; }
H="$(esc "$HOME")"
# The hub is wherever AI_DEV_HOME points, which is not necessarily ~/.ai-dev.
A="$(esc "$AI_DEV_HOME")"
FRAMEWORK_MSG="Blocked: the AI-DEV framework is read-only from a project session. Start a session in $AI_DEV_HOME to change it."

# ============================================================== DENY: secrets
# Naming one of these paths is the signal. Reading them is never part of a task.
CRED_PATHS="(${H}|~)/(\.ssh|\.aws|\.azure|\.gnupg|\.kube|\.docker/config\.json|\.netrc|\.npmrc|\.pypirc|\.git-credentials|\.config/gcloud|\.config/gh|\.password-store|\.local/share/keyrings|\.gnome2/keyrings|\.mozilla|\.thunderbird|\.config/google-chrome|\.config/chromium|\.config/microsoft-edge|\.config/BraveSoftware|\.config/vivaldi|\.config/opera|\.config/keepassxc|\.local/share/1Password|snap/firefox|\.var/app/org\.mozilla)"
if m "$CRED_PATHS"; then
  # ~/.codex and ~/.claude are managed by this framework; only their auth files
  # are secret, and those are matched separately below.
  deny cred-path "Blocked: this path holds credentials, keys, browser profiles or a password store. AI-DEV never reads it. If the human needs it, they do it themselves."
fi
if m "(${H}|~)/\.codex/auth\.json|(${H}|~)/\.claude/\.credentials\.json"; then
  deny cred-file "Blocked: agent authentication credentials are never read, copied, printed or committed."
fi
if m '/etc/(shadow|gshadow|sudoers)\b'; then
  deny cred-file "Blocked: system credential file."
fi
if m '\b(secret-tool|keyctl|gnome-keyring-daemon|kwalletcli|pass show|bw get|op read)\b'; then
  deny keyring "Blocked: OS keyring / password store access."
fi
if m 'Login Data|Cookies\.sqlite|cookies\.sqlite|key[34]\.db|logins\.json'; then
  deny browser-cred "Blocked: browser credential or cookie store."
fi

[ "$TOOL_NAME" = "Bash" ] || {
  # File tools: also protect the framework itself, then stop.
  #
  # Matched on the NORMALISED path, not the raw one. The credential rules above
  # already run against $NORM, so a file tool handed `$AI_DEV_HOME/core/x` or
  # `~/.ai-dev/core/x` would otherwise be compared as a literal string, miss the
  # resolved hub, and fall through to `pass` — the one rule on this branch
  # spelled differently from every other rule in the file.
  NFILE="${FILE//\$\{AI_DEV_HOME\}/$AI_DEV_HOME}"
  NFILE="${NFILE//\$AI_DEV_HOME/$AI_DEV_HOME}"
  NFILE="${NFILE//\$\{HOME\}/$HOME}"
  NFILE="${NFILE//\$HOME/$HOME}"
  NFILE="${NFILE//\~\//$HOME/}"
  case "$NFILE" in
    "$AI_DEV_HOME"|"$AI_DEV_HOME"/*|"$HOME/.ai-dev"|"$HOME"/.ai-dev/*)
      case "$CWD" in
        "$AI_DEV_HOME"|"$AI_DEV_HOME"/*) pass ;;
        # Read, Glob and Grep cannot write anything, and the rule being enforced
        # here is "the framework is READ-ONLY from a project session". Refusing
        # them would contradict the message they are refused with, and would
        # make the hub unsearchable from the projects it governs, for no
        # security gain. The credential rules above have already run.
        *) case "$TOOL_NAME" in Read|Glob|Grep) pass ;; esac
           deny framework-write "$FRAMEWORK_MSG" ;;
      esac ;;
  esac
  pass
}

# ============================================ DENY: downloaded script execution
if m '\b(curl|wget)\b[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z|k|da)?sh\b' \
  || m '\b(curl|wget)\b[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(python3?|perl|ruby|node|php)\b' \
  || m '\b(ba|z|k)?sh\b[[:space:]]+(-[a-z]+[[:space:]]+)*<\([[:space:]]*(curl|wget)' \
  || m '\b(ba|z|k)?sh\b[[:space:]]+-c[[:space:]]+["'"'"']?\$\([[:space:]]*(curl|wget)' \
  || m '\b(python3?|node|ruby|perl)\b[[:space:]]+-[ce][[:space:]].*\b(urlopen|requests\.get|fetch\()' ; then
  deny pipe-to-shell "Blocked: never pipe downloaded content into an interpreter. Download to a file, read it, then decide. Prefer the distro package manager or a pinned release."
fi

# ================================================== DENY: catastrophic to disk
if m '\brm\b([[:space:]]+-[[:alnum:]-]+)*[[:space:]]+(-[[:alnum:]-]+[[:space:]]+)*(/|/\*|--no-preserve-root)([[:space:]]|$)' \
  || m '\brm\b[^;|&]*[[:space:]]--no-preserve-root' \
  || m "\brm\b[^;|&]*[[:space:]](${H}|${H}/\*|~|~/\*)([[:space:]]|$)" \
  || m '\brm\b[^;|&]*[[:space:]]/(etc|usr|var|bin|sbin|boot|lib|lib64|opt|srv|root|dev|proc|sys)(/\*)?([[:space:]]|$)' ; then
  deny rm-catastrophic "Blocked: recursive removal targeting the filesystem root, a system directory, or the home directory."
fi
if m '\bmkfs(\.[[:alnum:]]+)?\b|\bmke2fs\b|\bfdisk\b[^|;&]*[[:space:]]/dev/|\bparted\b[^|;&]*[[:space:]]/dev/|\bwipefs\b|\bsgdisk\b|\bblkdiscard\b'; then
  deny disk-format "Blocked: filesystem/partition-destroying operation."
fi
if m '\bdd\b[^|;&]*[[:space:]]of=/dev/(sd|nvme|vd|hd|mmcblk|loop|disk|sr)'; then
  deny dd-raw-write "Blocked: raw write to a block device."
fi
if m '>[[:space:]]*/dev/(sd|nvme|vd|hd|mmcblk)[a-z0-9]*'; then
  deny dd-raw-write "Blocked: shell redirection onto a block device."
fi
if m '\bchmod\b[^|;&]*[[:space:]]-[a-zA-Z]*R[a-zA-Z]*[[:space:]]+[0-7]{3,4}[[:space:]]+/([[:space:]]|$)' \
  || m "\bchown\b[^|;&]*[[:space:]]-[a-zA-Z]*R[a-zA-Z]*[^|;&]*[[:space:]]/([[:space:]]|$)"; then
  deny perm-recursive-root "Blocked: recursive ownership/permission change on the filesystem root."
fi
if m ':\(\)[[:space:]]*\{[[:space:]]*:\|:'; then
  deny fork-bomb "Blocked: fork bomb."
fi

# ================================================ DENY: host power / protection
if m '\b(shutdown|poweroff|halt|reboot)\b' \
  || m '\bsystemctl\b[^|;&]*\b(poweroff|reboot|halt|suspend|hibernate|kexec)\b' \
  || m '\binit\b[[:space:]]+[06]([[:space:]]|$)'; then
  deny power "Blocked: shutting down or rebooting this machine is the human's decision."
fi
if m '\bufw\b[^|;&]*[[:space:]](disable|reset)\b' \
  || m '\bsystemctl\b[^|;&]*\b(stop|disable|mask)\b[^|;&]*\b(ufw|firewalld|nftables|iptables|apparmor|auditd|fail2ban|snapd\.apparmor)\b' \
  || m '\bsetenforce\b[[:space:]]+0\b|\baa-(teardown|disable|complain)\b' \
  || m '\biptables\b[^|;&]*[[:space:]]-F\b|\bnft\b[^|;&]*[[:space:]]flush[[:space:]]+ruleset' \
  || m '\bsysctl\b[^|;&]*apparmor_restrict_unprivileged_userns[[:space:]]*=[[:space:]]*0'; then
  deny security-disable "Blocked: disabling the firewall or a mandatory access control system."
fi
if m '/var/run/docker\.sock|/run/docker\.sock'; then
  deny docker-sock "Blocked: exposing the Docker socket grants root on this host. Never mount or proxy docker.sock."
fi
if m '\-\-dangerously-skip-permissions|\-\-dangerously-bypass-approvals-and-sandbox|\-\-dangerously-bypass-hook-trust|bypassPermissions|danger-full-access|\-\-yolo\b'; then
  deny bypass-attempt "Blocked: permission/sandbox bypass flags are never used in normal development."
fi

# ============================================== DENY: framework self-protection
#
# The hub is wherever AI_DEV_HOME points. Matching only the literal `~/.ai-dev`
# would leave every installation somewhere else — a clone under ~/code, a shared
# /opt checkout, a CI workspace — without this rule, while the file-tool branch
# above kept enforcing it. Both branches resolve the hub the same way.
#
# Both spellings are matched, and neither depends on the other being true: $A is
# the resolved hub, and the default location stays covered so a
# command aimed at ~/.ai-dev is refused even when AI_DEV_HOME points elsewhere.
if m "(${A}|${H}/\.ai-dev)\b"; then
  case "$CWD" in
    "$AI_DEV_HOME"|"$AI_DEV_HOME"/*) : ;;
    *)
      if m "\b(rm|mv|cp|tee|truncate|chmod|chown|ln|sed[^|;&]*-i|install)\b[^|;&]*(${A}|\.ai-dev)" \
        || m ">[[:space:]]*[^[:space:]]*(${A}|\.ai-dev)" \
        || m "\bgit\b[^|;&]*-C[[:space:]]+(${A}|${H}/\.ai-dev)[^|;&]*\b(commit|checkout|reset|clean|push|rm)\b"; then
        deny framework-write "$FRAMEWORK_MSG"
      fi
      # A `cd` into the hub relocates every LATER clause of the same command,
      # and the rules above bind a verb to a path within a single clause
      # (`[^|;&]*` stops at the separator). So `cd <hub> && rm core/x` names the
      # hub in one clause and mutates it in the next, and neither clause matches
      # on its own. Pair them: a hub-targeted `cd` anywhere in the command, plus
      # a mutating verb or a RELATIVE redirection anywhere in it, is a write to
      # the framework. An absolute redirection is excluded deliberately —
      # `cd <hub> && grep -r x . > /tmp/out` reads the hub and writes elsewhere,
      # which is allowed from any project.
      if m "(^|[;&|[:space:]])cd[[:space:]]+[\"']?(${A}|${H}/\.ai-dev)([\"'/[:space:];&|]|$)" \
        && { m '\b(rm|mv|cp|tee|truncate|chmod|chown|ln|install|dd)\b' \
          || m '\bsed\b[^|;&]*-i' \
          || m '>[[:space:]]*[^/[:space:]]' \
          || m '\bgit\b[^|;&]*\b(commit|checkout|reset|clean|push|rm|apply)\b'; }; then
        deny framework-write "$FRAMEWORK_MSG"
      fi ;;
  esac
fi

# ================================================== ASK: consequential but real
if m '(^|[;&|[:space:]])sudo([[:space:]]|$)|(^|[;&|[:space:]])doas([[:space:]]|$)|\bpkexec\b'; then
  ask sudo "Elevated privileges. Confirm this is what you want."
fi
# Detect the git PUBLICATION verb `push`, not any later word "push". `git
# stash push`, `git commit -m "push"`, `git rebase -i "and push"` are all
# local operations. `push` must appear as the top-level git subcommand —
# after zero or more global options — for this to be a publication.
if m '\bgit\b([[:space:]]+(-[^[:space:]|;&]+([[:space:]]+[^-[:space:]|;&][^[:space:]|;&]*)?|-c[[:space:]]+[^[:space:]|;&]+))*[[:space:]]+push\b'; then
  ask git-push "Publishing commits to a remote. AI-DEV never pushes without your approval."
fi
if m '\bgit\b[^|;&]*\breset\b[^|;&]*--hard' \
  || m '\bgit\b[^|;&]*\bclean\b[^|;&]*-[[:alnum:]]*[fd]' \
  || m '\bgit\b[^|;&]*\b(checkout|restore)\b[^|;&]*[[:space:]]\.([[:space:]]|$)' \
  || m '\bgit\b[^|;&]*\b(rebase|filter-branch|filter-repo)\b' \
  || m '\bgit\b[^|;&]*\bbranch\b[^|;&]*[[:space:]]-D\b' \
  || m '\bgit\b[^|;&]*\breflog\b[^|;&]*\bdelete\b' \
  || m '\bgit\b[^|;&]*\bstash\b[^|;&]*\b(drop|clear)\b'; then
  ask git-destructive "This discards work that may not be recoverable."
fi
if m '\b(npm|pnpm|yarn|bun)\b[^|;&]*\bpublish\b' \
  || m '\btwine\b[^|;&]*\bupload\b|\b(poetry|uv)\b[^|;&]*\bpublish\b' \
  || m '\bcargo\b[^|;&]*\bpublish\b|\bgem\b[^|;&]*\bpush\b|\bmvn\b[^|;&]*\bdeploy\b' \
  || m '\bgh\b[^|;&]*\brelease\b[^|;&]*\bcreate\b' \
  || m '\bdocker\b[^|;&]*\bpush\b|\bpodman\b[^|;&]*\bpush\b'; then
  ask publish "This publishes an artifact outside this machine."
fi
if m '\bterraform\b[^|;&]*\b(apply|destroy)\b|\bpulumi\b[^|;&]*\b(up|destroy)\b' \
  || m '\b(serverless|sls)\b[^|;&]*\bdeploy\b|\bvercel\b[^|;&]*--prod\b' \
  || m '\bnetlify\b[^|;&]*\bdeploy\b|\b(fly|flyctl)\b[^|;&]*\bdeploy\b' \
  || m '\bansible-playbook\b|\beb\b[[:space:]]+deploy\b|\bcap\b[^|;&]*\bdeploy\b'; then
  ask deploy "This deploys to external infrastructure."
fi
if m '\bkubectl\b[^|;&]*\b(delete|drain|cordon|apply|replace|scale|rollout)\b' \
  || m '\bhelm\b[^|;&]*\b(install|upgrade|uninstall|delete|rollback)\b' \
  || m '\baws\b[^|;&]*\b(delete|terminate|remove|rm|deregister|destroy)\b' \
  || m '\bgcloud\b[^|;&]*\bdelete\b|\baz\b[^|;&]*\bdelete\b|\bdoctl\b[^|;&]*\bdelete\b'; then
  ask cloud-mutating "This changes or destroys cloud/cluster resources."
fi
if m '\bdocker\b[^|;&]*\bsystem[[:space:]]+prune\b[^|;&]*-a|\bdocker[[:space:]]+volume[[:space:]]+rm\b'; then
  ask docker-destructive "This deletes Docker images or volumes that may not be rebuildable."
fi
if m '\b(dropdb|mysqladmin[[:space:]]+drop)\b' \
  || mi 'DROP[[:space:]]+(DATABASE|TABLE|SCHEMA)\b|TRUNCATE[[:space:]]+TABLE\b'; then
  ask db-destructive "This destroys database data."
fi

pass
