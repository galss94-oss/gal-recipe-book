cd "/Users/galsamuchian/Documents/Claude" && cat >> DASHBOARD-EDITING-GUIDE.md <<'GUIDE_EOF'

## 7. Log under the label that matches who you are

`changelog.py --add "<who>" "<what>"` — the first argument is the actor. On 03/09/2026 all six
entries in the window said `daily triage`, including work done by chat sessions. The label
carried no information.

- The scheduled task logs `daily triage`.
- A chat session logs `chat: <what it was doing>` — e.g. `chat: overview rebuild`.
- A one-off task logs its own name.

This is not bookkeeping. STEP 0a of `daily-dashboard-triage` exists so a run can see that
another session touched a file it is about to edit; if every entry claims to be the daily task,
that check is blind. Rule 21 — ps the regen directory before the first edit — was earned by
exactly that blindness, when a chat session was mid-build in the stock artifact while the task
was about to edit it.

Reading the log is also how anyone judges whether the schedule is behaving. Six entries labelled
`daily triage` across one evening reads as six scheduled runs; it was one chat conversation.
GUIDE_EOF
