# Server tests

```bash
python server/tests/test_api_binding.py           # the binding — add -v for per-test output
python server/tests/test_client_conformance.py    # the reference client vs the spec
```

No dependencies — stdlib `unittest`, no sockets, no Electron. `test_api_binding`
drives `api_binding.handle_message()` directly against the tracked fixture tree
(`server/data/content.test`), so a full run takes about four seconds.

`test_client_conformance` is CONFORMANCE.md §E made mechanical: it parses §4.7's
vocabulary and §4.8's context table out of `docs/spec/` and diffs them against
`client/web/src/main.ts`, in **both** directions — a command the client offers
that the spec does not define fails just as loudly as one the spec requires and
the client lacks. It reads both files as text and imports nothing.

⚠ It proves the client offers the right *commands in the right contexts*, and
nothing about whether they behave correctly. CONFORMANCE.md §A–§D are answerable
"by looking, not by reasoning about the code"; no test here replaces that pass.

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

**The suite leaves the fixtures untouched — but only the content tree is
read-only.** It exercises the validation paths that reject before writing rather
than the success paths that create content, so `content.test/` is never dirtied
and the paid-page fixture is never consumed.

`mail.test/` is different and cannot be: reading a message marks it read and
rewrites the mailbox JSON. So the suite **copies the mail tree to a temp
directory** at import and points the server at the copy. Both trees are tracked
— they are the fixtures, and a clone without them has nothing to test against —
and the two tests that need to write (`PersistenceRoundTrip`) copy the content
tree the same way.

Set `COMPUNET_MAIL_DIR` or `COMPUNET_CONTENT_DIR` to override either, e.g. to
run the suite against a real deployment's data.

## Adding to it

When a run reports a bug, add the failing sequence here *before* fixing it, and
name the finding. If a fix is worth making, the sequence that exposed it is
worth keeping — that is the whole lesson of the runs so far.
