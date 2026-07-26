# Server tests

```bash
python server/tests/test_api_binding.py       # add -v for per-test output
```

No dependencies — stdlib `unittest`, no sockets, no Electron. It drives
`api_binding.handle_message()` directly against the tracked fixture tree
(`server/data/content.test`), so a full run takes about four seconds.

## Why these exist

Every clean-room run of Binding B has found bugs introduced by the *previous*
round of fixes, and the only regression detector was the next clean-room run — a
complete client build, days later. Each test names the finding it guards
(`docs/spec/VALIDATION.md`).

Three bug classes account for nearly all of them, and the suite is organised
around them rather than around functions:

| Class | Why it recurs |
|---|---|
| **Reply-type inference** | The binding serializes *session state* rather than what the command produced, so a stale `show_page` or `mail_mode` makes a navigation command answer with a frame, a download descriptor, or the wrong listing. Binding A never has this — it returns the bytes the command made |
| **Listing scoping** | `page` and `index` name entries of the listing *on screen*; anything resolved against the whole tree or the whole mailbox is wrong |
| **Invariants** | A listing is never empty and never exceeds eleven rows; some fields are always present |

## Two rules that matter

**Never share a session between tests.** Every regression here was a state bug
that only appears in a *sequence* — a shared session lets one test mask the
next, which is how they shipped in the first place.

**The suite is read-only.** It exercises the validation paths that reject before
writing, not the success paths that create content, so running it does not dirty
the fixture tree or consume the paid-page fixture.

## Adding to it

When a run reports a bug, add the failing sequence here *before* fixing it, and
name the finding. If a fix is worth making, the sequence that exposed it is
worth keeping — that is the whole lesson of the runs so far.
