# Test content tree

A content tree carrying the **fixtures a validation run needs**. Unlike `server/data/content/`,
which is live data and not tracked in git, this one **is** tracked — so a clean-room run or a
harness gets the same starting conditions on any machine.

Point a server at it with an environment variable:

```bash
COMPUNET_CONTENT_DIR=server/data/content.test python server/run_api_only.py
COMPUNET_DATA_DIR=server/data.test python server/compunet_server.py   # content + mail + votes
```

`COMPUNET_CONTENT_DIR` swaps only the content; `COMPUNET_DATA_DIR` moves mail and votes too,
which is usually what a validation run wants — test uploads and test mail then land here instead
of in real data.

## What is in it, and why

| Fixture | Where | Exercises |
|---|---|---|
| `"open_upload": true` | The Jungle (600) | Uploads succeeding, `directory_full`, latent-directory creation (§8.3.2, §7.4) — **all three fail identically without it** |
| `"open_upload": false` | THE ZOO (699) | That a child can **stop** the inheritance, and that its owner is still not locked out |
| An authored **`MORE` entry** | The Jungle (909) | Overflow the way the real service does it (§7.6): The Jungle holds 10 entries plus a `MORE` directory you enter like any other. Authored directories do **not** paginate |
| **15 mail messages** | `mail.test` | The *generated*-listing exception — a mailbox is assembled by the server, so it carries a synthetic `MORE >>>>` row that pages when selected |
| `PAY TO VIEW`, £1.50 | inside `MORE` | The **paid** half of the `SHOW`/`BUY` gate (§8.6.4) |
| `PAID PAGE`, £2.50 | inside `MORE` | The **owned** half — blank price, no gate, when the account has already bought it |

## Keeping it usable

**The paid page must stay unbought between runs.** Buying it is the test, and afterwards it shows
no price and exercises nothing. Reset the account's `purchased` list (and credit) in
`server/cfg/users.json` afterwards — the reference account is `TEST` with `purchased: [905]`,
which leaves 905 owned and 906 available to buy.

**Run as a normal account, not an administrator.** Admins bypass `_can_upload_here` entirely, so
a run as admin proves nothing about the permission rules — which is why the reference account is
a GOLD user rather than ADMIN.

**Uploads write into this tree.** If a run leaves test pages behind, `git status` will show them
and `git checkout` will clear them — which is the main reason this tree is tracked and the live
one is not.
