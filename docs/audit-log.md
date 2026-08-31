# The audit log

What Compunet Reborn records about who did what, where the records come from, and
how to read them back.

The log is `server/data/audit.jsonl` — one JSON object per line, appended, never
rewritten in normal operation. It is written only by the server; the website has
no access to the file and records events through `POST /api/audit`.

---

## The rule

**An action is audited by the function that performs it, not by the caller that
reached it.**

This is the whole design, and it exists because the alternative failed. Auditing
used to sit in the command handlers, so whether an action was recorded depended on
which client the user came through: mail sent from a C64 or the PETSCII terminal
was logged, and the same mail sent through the JSON API was not — because Binding B
calls the shared `_complete_mail_send` directly rather than going through Binding
A's handler.

`complete_content_upload` always had its `audit_log` call *inside* it, which is
why uploads never had that gap. Same file, seventy lines apart, one right and one
wrong (#127).

⚠ **The rule protects the record, not the behaviour**, and uploads showed the
difference. The terminal audited its uploads correctly — it had copied the call
along with everything else — while its copy of the *writer* had quietly drifted
from the shared one. So the log said the right thing about a page that had been
stored by different rules. Auditing inside the shared function only helps if the
function really is shared; the terminal now calls
`compunet_server.complete_content_upload` like the other two.

So: when adding a feature, put the `audit_log` call in the function that does the
work. A future binding that reuses it inherits the record for free.

### Where this cannot apply

Two actions genuinely have no shared function, and each keeps its own call with a
comment saying why:

- **Terminal downloads** — the terminal XMODEMs `page.frames[0]` directly and never
  touches the staged-download mechanism the other two share. It also audits on
  *success*, after the transfer completes, where the others audit on acceptance.
- **Terminal mail** — `terminal.py` has its own delivery loop rather than calling
  `_complete_mail_send`. That duplication is a separate problem; the audit simply
  follows it.

And one action is audited in the right place but **cannot derive `via` and `ip`**
there:

- **Partyline entry** — `partyline_log('join', …)` is the shared function all four
  surfaces reach, so `partyline_entered` is written correctly from every one of
  them. But it never sees a session: each surface holds the address somewhere
  different, so the caller must hand `via=` and `ip=` over as named arguments
  (never inside `**details`, which would put an address into `partyline.jsonl`,
  the chat history). Until the admin console was proxied through the website
  (#144) no caller passed either, so every `partyline_entered` in the older
  history says `"via": null` with no address at all — the one event that cannot
  answer "from where".

---

## Fields

Every entry has:

| Field | Always | Meaning |
|---|---|---|
| `time` | yes | `YYYY-MM-DD HH:MM:SS`, server local time |
| `event` | yes | One of the names below. Enforced — see *The registry* |
| `kind` | yes | The event's category, derived from the registry |
| `user` | usually | The Compunet ID. Absent on `missing_frame`, which is a server fault |
| `via` | where known | Which surface: `c64`, `amiga`, `terminal`, `api`, `web`, `admin` |
| `ip` | where known | The client address |

Anything else is event-specific — `page`, `title`, `to`, `subject`, `changed`, and
so on.

`via` and `ip` are **derived from the session**, not passed by each call site:

```python
audit_log('page_read', session=self, page=child.page_num)
```

They were previously per-call-site arguments, which is why they appeared on all ten
of `terminal.py`'s events and almost none of Binding A's. Pass `session` and a new
call site cannot omit them. Where there is no session — the admin REST routes —
pass `via=` and `ip=` explicitly.

> **⚠ `ip` must be the VISITOR's address, and the peer is never it.** Every way in
> reaches the server through something else: the web and desktop clients arrive via
> the Cloudflare tunnel, and the website talks to the admin API from its own
> container. Reading the socket peer therefore records infrastructure — the tunnel
> (`172.18.0.4`) or the website (`172.18.0.3`) — against real user actions.
>
> One definition resolves it and **everything must go through it**:
> `compunet_server.client_ip_from_request(request)`, which prefers
> `CF-Connecting-IP`, then the first entry of `X-Forwarded-For`, then the peer — so
> a direct connection still records correctly. `api_binding._client_ip(request)`
> delegates to it rather than repeating the rule, and `_api_caller_ip(request)`
> covers the admin API's own case by reading the `X-Compunet-Client-IP` the website
> sends.
>
> The website's WebSocket proxy is the same problem one layer further out: the
> admin console's socket is opened by the website container, so the upstream
> handshake carries `X-Forwarded-For: <the admin's address>` and
> `client_ip_from_request` picks it up. Without that, every `partyline_entered`
> from the console would record the website.
>
> This was wrong for as long as the field existed (#135), and the reason is worth
> keeping: **the helper was right, and two of three call sites used it.** Nothing
> failed, nothing logged an error, and the tests passed — they asserted `ip` was
> *present*, never that it was *correct*. `test_audit.py` now checks both, including
> a structural check that no handler reads the peer directly, because the next way
> this returns is a new route written by someone who has not read this page.

### `via` values

| Value | Surface |
|---|---|
| `c64` | Binding A, C64 client |
| `amiga` | Binding A, native Amiga client. Set at identification by `identify_binding_a_client()`, which writes `is_amiga` **and** this label together |
| `terminal` | PETSCII terminal, port 6401 |
| `api` | Binding B — the web client, the Electron app, and any third-party client |
| `web` | The website itself (registration, password reset) |
| `admin` | An administrative action through the REST API |

⚠ **Entries written before 1.4.0 record every Amiga session as `c64`.** The label was set
to `c64` when the socket opened and identification updated only `session.is_amiga`, which
`audit_via()` never consults once an explicit value is present — so the two Binding-A
machines are indistinguishable in the older history. Nothing can recover it retroactively:
a `via: c64` entry from before the fix may have come from either machine. Filtering
`via=amiga` over that period returns nothing, which is an artefact, not a fact about usage.

---

## The registry

`compunet_server.AUDIT_EVENTS` maps every event name to its kind, and
`audit_log` **raises on a name that is not in it**. `POST /api/audit` rejects one
with a 400.

That is deliberate. An undeclared name would be written happily and then be
invisible to every filter that knows the vocabulary — a record that exists but
cannot be found. Adding an event means adding a line to the registry, which is also
what keeps this document honest.

Names are `noun_verbed`, past tense. The vocabulary previously grew ad hoc —
`page_deleted` and `header_removed` against `upload` and `vote` — with nothing for
a new feature to conform to.

### `kind`

`kind` exists so the viewer can separate signal from volume. On the live log
`browse` is 43% of all entries; `admin` is the handful anyone auditing actually
wants.

| Kind | What it covers |
|---|---|
| `browse` | Reading. High volume — filter it out to see everything else |
| `content` | Anything that changes a page or a directory |
| `mail` | Courier |
| `session` | Connecting, authenticating, accounts |
| `admin` | Administrative action. The events an audit log exists for |
| `partyline` | Chat, including moderation |
| `operational` | Server faults, not user actions. No `user` |

### Every event

### `content`

- `directory_created`
- `directory_settings_changed`
- `header_removed`
- `header_set`
- `page_bought`
- `page_deleted`
- `page_downloaded`
- `page_life_extended`
- `page_moved`
- `page_renamed`
- `page_reordered`
- `page_uploaded`
- `page_voted`

### `mail`

- `mail_sent`

### `session`

- `login_failed`
- `login_succeeded`
- `password_changed`
- `password_reset`
- `password_reset_requested`
- `session_ended`
- `session_started`
- `signup_completed`

### `admin`

- `broadcast_sent`
- `registration_rejected`
- `registration_requested`
- `user_deleted`
- `user_updated`

### `partyline`

- `partyline_banned`
- `partyline_entered`
- `partyline_kicked`
- `partyline_unbanned`

### `browse`

- `mail_opened`
- `page_read`

### `operational`

- `missing_frame`

---

## Notes on particular events

**`page_uploaded`** carries `action` — `uploaded` for a new page, `replaced` when
it overwrote one that was already there. Without it the event cannot distinguish
someone publishing their own work from someone overwriting a page an editor
owned, which is the version of the question anybody actually asks. It was
recorded only by the terminal's own copy of the writer; folding that copy into
the shared one gave it to every surface.

**`user_updated`** carries `changed`, a list of `field: old -> new`. "ADMIN edited
ZARD" is close to useless a month later, and this is the endpoint where credit is
adjusted and editor rights are granted. **Passwords are named but never valued** —
`password: changed` — because putting credential material in a log an admin reads
in a browser would be its own problem.

**`password_changed` vs `user_updated`.** Both come from `PUT /api/users/{id}`. A
user changing their own password sends `self_service: true` and is recorded as
`password_changed` with `via=web`; anything else is an administrative edit. Without
that distinction, routine self-service would sit among the credit adjustments.

**`registration_rejected`.** `DELETE /api/pending/{token}` serves both approval and
rejection — approving consumes the token and then creates the account, rejecting
consumes it and creates nothing. The caller passes `?outcome=approved` so the two
are distinguishable; an approval is recorded as `signup_completed` when the account
is created.

**Declined downloads are not recorded.** `page_downloaded` fires when the user
accepts and the bytes are handed over. A decline means they obtained nothing.

**Website browsing is not recorded.** Reading a page *on the service* is
`page_read`; browsing the website around it is not audited.

---

## Reading it back

`GET /api/audit` (admin API, port 6403 — internal only) and the admin viewer at
`/admin/audit`.

| Parameter | Effect |
|---|---|
| `page`, `per_page` | Paging, newest first. `per_page` caps at 500 |
| `user` | Exact match, case-insensitive |
| `event` | Repeatable, or comma-separated |
| `kind` | Repeatable, or comma-separated |
| `via` | Exact match |
| `ip` | Exact match |
| `from`, `to` | `YYYY-MM-DD`, inclusive |
| `q` | Free text across every field, so titles and subjects are findable |
| `count=exact` | Scan the whole log for a true match count |

### Why the reader goes backwards

`_audit_iter_reversed` reads the file from the end in 64 KB blocks, stitching
partial lines across boundaries. The endpoint stops as soon as the requested page
is filled.

The previous implementation parsed the entire file into memory on every request,
reversed it and sliced out one page. That was imperceptible at 6,838 entries and
would have stayed imperceptible for a while — but filtering on top of it costs the
same full scan every time, and the log only grows. Reading backwards means the
common case (recent events, however filtered) costs a couple of blocks no matter
how large the file gets.

**An exact match count is the one thing that cannot be cheap**, because knowing how
many entries match means looking at all of them. So it is not claimed unless it was
established: `matched_exact` is `true` only when the scan reached the start of the
file. Otherwise `matched` is a floor and `has_more` says whether another page
exists — which is what a pager actually needs. The viewer requests `count=exact`
only when a filter is set, because that is when the number is worth the scan.

---

## Migration

`server/migrate_audit_log.py` renames historical events to this vocabulary and adds
`kind`. It takes a backup first and refuses to run if one already exists. Run it
with `--dry-run` to see what it would do.

The live log was migrated at 1.4.0: 6,838 entries, 6,080 renamed, none
unrecognised.

---

## Not covered here

**Retention and rotation.** Nothing deletes old entries, and nothing rotates the
file. Worth deciding — filtering makes the log more useful, which makes deleting
from it a harder call later.

**Tamper-evidence.** The log is an ordinary append-only file with no signing or
chaining. An admin with shell access can edit it. That is a deliberate scope
decision, not an oversight: the log is both an activity record and an
administrative one, in a single file, filtered at the viewer.
