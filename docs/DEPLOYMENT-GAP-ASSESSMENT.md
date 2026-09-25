# Deployment Gap Assessment - InnoCalc on the Shared Application Host

Assessed 24 September 2026 against the InnoResource hosting plan in
`C:\CODING\INNORESOURCE - TS BRANCH\README - docker-instructions.md` (the story, Prompts 1-3
and the tenant contract). That plan hosts several internal applications on one Ubuntu server,
each as a Docker tenant behind a shared Caddy reverse proxy, reachable from the office LAN and
VPN only, with a production and a preview instance per application.

| Step | Scope | Status |
|------|-------|--------|
| 1 | Application ready to be a good tenant (Prompt 1 equivalent) | **Implemented** here |
| 2 | Shared `server-platform` repository (Caddy, ufw, add-app, backups mirror) | Not started - waiting on IT |
| 3 | Containerisation and deploy scripts (Prompt 3 equivalent) | Not started |

## 1. Current deployment against the target

| Aspect | Today | Tenant target |
|--------|-------|---------------|
| Where it runs | Each designer's PC: `InnoCalc.bat` -> `apps/manager/start.bat` -> `server.py` | One container per instance (prod, preview) on the host |
| Listening | `127.0.0.1:8125` only | `0.0.0.0:8125` inside the container, no published port; Caddy on the `edge` network |
| Application data | Per-PC `apps/manager/data` (people, registry, discovery index) | One `/data` per instance on local ext4, snapshotted to `/backups` |
| Project data | Written directly to `J:\Active Projects` | Same share, mounted on the host; read-write for prod, read-only for preview |
| Sign-in | Type an Innovis email, no password | Entra ID once at the edge; identity header trusted only from Caddy |
| Desktop helpers | tkinter folder picker, Explorer, Outlook opens `.eml` | Not possible on a server |
| PDF | Installed Edge/Chrome on Windows | Chromium inside the image |
| Releases | Pull and run | Tagged image; preview first, then prod; rollback by tag |

## 2. How the plan maps onto InnoCalc

InnoCalc calls no rate-limited external API, so the plan's Total Synergy budget does not apply.
The shared resource InnoCalc must protect is the **projects share**.

| InnoResource (Prompt 1) | InnoCalc equivalent |
|-------------------------|---------------------|
| Frozen mirror: no Synergy refresh on preview, 409 | `ICM_READ_ONLY`: no writes to the projects share, 409 |
| `INNORES_TAB_ACCESS` (viewer ... admin) | `ICM_TAB_ACCESS` (user, admin) and `ICM_MODULE_ACCESS` for enabled modules not ready for everyone |
| `INNORES_TRUSTED_PROXIES`, `INNORES_ALLOWED_HOSTS`, HSTS with `INNORES_COOKIE_SECURE` | `ICM_TRUSTED_PROXIES`, `ICM_ALLOWED_HOSTS`, HSTS with `ICM_HTTPS` |
| `sso` mode; refuse an insecure secret key | `ICM_AUTH_MODE=proxy`. The manager holds no signing secret (dev sessions are random in-memory tokens; proxy mode needs none), so the equivalent refusal is proxy mode combined with the in-app SSO flow |
| uvicorn `--no-proxy-headers`, forwarded headers applied by `app/proxy.py` | The standard-library server never rewrites the peer; `icm/proxy.py` applies forwarded headers only from trusted peers |
| Hourly SQLite snapshot, `scripts/restore_snapshot.py` | Snapshot of the data folder, `python -m icm.backup restore` |
| `/api/health` 503 when the database is unreachable | `/api/health` 503 when the data folder cannot be written |
| Read-only root filesystem, arbitrary UID | Same: writes go only to `ICM_DATA_DIR`, `ICM_BACKUP_DIR`, the projects share and the temp directory |

## 3. Step 1 - implemented

* [apps/manager/icm/config.py](../apps/manager/icm/config.py): every `ICM_*` setting read and
  validated once; bad tab/module/role names, bad proxy addresses, proxy mode with in-app SSO,
  backups inside the data folder and unwritable folders stop the service with the reason.
  Existing folders are accepted whoever owns them.
* [apps/manager/icm/proxy.py](../apps/manager/icm/proxy.py) and
  [apps/manager/server.py](../apps/manager/server.py): Host allow-list (400), identity header
  refused and logged from untrusted peers (401), proxy sign-in mode, forwarded origin only from
  trusted peers, HSTS with `ICM_HTTPS`, read-only 409 on every share-writing route (and no
  verifier-return scan), tab and module gates (403), unauthenticated `/api/health`, and a
  data-folder lock so two managers never share one data folder.
* Server mode (any non-loopback `ICM_HOST`): folder picker, Explorer and browser launch
  withdrawn; every browser-supplied path confined to `ICM_ROOT`. Previously any signed-in user
  could have listed server folders or copied a server file into a project through PDF import.
* [apps/manager/icm/backup.py](../apps/manager/icm/backup.py): scheduled and on-demand
  snapshots with manifest hashes, JSON checks, retention, and a verified restore that refuses a
  running manager, unsafe archive entries and interrupted writes (unless `--force`).
* [packages/calcpad/export.py](../packages/calcpad/export.py): Chromium found on Linux or via
  `INNOCALC_BROWSER`; extra flags via `INNOCALC_BROWSER_ARGS`.
* Front end: proxy sign-in without the email dialog, withheld tabs hidden and never opened,
  read-only notice with Save disabled.
* [.env.example](../.env.example), `.gitignore` (`.env`, `deploy/*.env`, manager backups), the
  manager README, and [tests/test_deployment.py](../tests/test_deployment.py).

Desktop behaviour with no settings is unchanged. No engineering module, library, QA or
collation logic changed.

## 4. Remaining gaps

**Blockers for Step 3** must be resolved before an image is worth building. **Go-live** items
must be resolved before staff use the server instance. **G4 and G5 are the two critical
steps**; their sign-off tests are in [DOCKER-DEPLOYMENT.md](DOCKER-DEPLOYMENT.md) (C1, C2).

Updated in v0.0.1: G1, G2 and G3 are resolved; G5's interim gate is now the default.

| # | Gap | Severity | Recommended resolution |
|---|-----|----------|------------------------|
| G1 | **Module source is not in the root repository.** | **Resolved v0.0.1** | Steel, Concrete Column and Calculation Pad are Git submodules pinned in `.gitmodules`; CI checks out recursively; `setup.bat` initialises missing submodules; `tooling release-check` refuses unpushed module commits. Before the first image, commit and push each module's local work and commit the updated pointers. Still exclude the stale root copies (`InnoCalcManager/`, `CalculationPad/`, `SteelMemberDesign/`, `ConcreteColumnDesign/`) from the image. |
| G2 | **Windows paths are persisted.** | **Resolved v0.0.1** | [apps/manager/icm/paths.py](../apps/manager/icm/paths.py): projects stored by `location` under the root, discovery root-relative, library/issue/QA paths project-relative with `/`; legacy records rewritten on first write and recognised on Linux through `ICM_LEGACY_ROOTS`; draft emails link through `ICM_SHARE_PATH`. Module inputs that hold file paths (Calculation Pad PDF/figure cells) remain - see ROADMAP. |
| G3 | **Per-user registries must be merged.** | **Resolved v0.0.1** | `python -m icm.merge <pc data folders> --into /data [--apply]`: dry-run report, backup first, refuses a running manager. |
| G4 | **CRITICAL - projects share from Linux and cross-platform locking.** Needs a CIFS mount on the host with a service account, owner mapped to the tenant UID, read-write into prod and read-only into preview. | **Critical - go-live** (code done; needs IT and sign-off) | Both platforms now take the same byte-0 byte-range lock (`msvcrt` / `fcntl.lockf`), which the CIFS client forwards to the file server; `python -m icm.locking hold|probe` runs sign-off tests C1.1-C1.2; `ICM_OWNS_PROJECTS=true` on prod makes PC copies refuse writes to a server-managed root, enforcing a single cut-over. Remaining: IT mount, then C1.1-C1.5 on the real share. |
| G5 | **CRITICAL - PDF printing in a container.** | **Critical - go-live** (image and CI proof in place; not yet run) | `Dockerfile` (Chromium, Carlito/Liberation/DejaVu, `HOME=/tmp`, `--no-sandbox --disable-dev-shm-usage` - decision recorded in DOCKER-DEPLOYMENT.md) and CI job `container-pdf` run the full PDF smoke inside the image non-root with a read-only root. Windows smoke passed twice on one PC. Package Export and Verification stay admin-only until C2.1-C2.5 pass. |
| G6 | **Desktop-only workflows need server replacements.** Picker, open folder, auto-opened Outlook draft and file-path entry are withdrawn in server mode, not replaced. | Go-live | Copyable UNC paths instead of Explorer; offer the `.eml` for download through `/api/file`; typed paths with project-number lookup (already available). |
| G7 | **Identity on a shared server.** Dev sign-in lets anyone act as anyone. InnoCalc records designer initials and verifier endorsement, so this matters more than for InnoResource. | Go-live | Open production to staff only once edge Entra ID sign-in is live and `ICM_AUTH_MODE=proxy`; until then a named pilot group only. |
| G8 | **Container and deploy artefacts** (Step 3): Dockerfile (Python 3.12 slim, Chromium, tzdata, `TZ=Australia/Adelaide` because stamps use local time, `PYTHONDONTWRITEBYTECODE=1`, `ICM_HOST=0.0.0.0`), `.dockerignore`, `deploy/compose.yml` (prod + preview, no ports, `edge`, `user:`, `read_only`, tmpfs `/tmp`, `/srv/innocalc/{prod,preview}/{data,backups}`, share mount rw/ro), `deploy/innocalc.caddy`, `deploy/prod.env.example` / `preview.env.example`, `deploy.sh`, `refresh-preview.sh`, `first-install.sh`, workstation snapshot pull. | Step 3 | Follow Prompt 3. The in-container backup is `docker compose exec innocalc-prod python -m icm.backup create`; the preview refresh stops preview, runs `python -m icm.backup restore <newest prod snapshot> --data-dir /data --force` in a one-off container and starts it again. The health probe must send the site's `Host`. |
| G9 | **Release discipline.** No Git tags (prod deploys only annotated `vX.Y.Z` tags); the CI workflow has never run; `main` is unprotected. Versions restarted at `v0.0.1` in the `vMajor.Patch.Minor` form (packages/innocalc_sdk/versioning.py). | Step 3 | Tag releases and keep the tag and `icm/version.py` aligned; protect `main` as in the plan's section 3I. |
| G10 | **Standard-library HTTP server.** No request-size limit or access log; one thread per connection. | Later | Adequate behind Caddy on the LAN for office load. Set `request_body max_size` and access logging in the Caddy site file. |
| G11 | **Single process only.** Sessions, locks and the PDF worker are in-process; a restart signs dev-mode users out. | Later | Run one replica per instance; proxy mode needs no sessions. |
| G12 | **Backup mirroring.** `/srv/innocalc/prod/backups` must reach the file server. | Step 2 | Covered by the platform's generic `sync-backups.sh` over `/srv/*/prod/backups`. The projects share remains under IT's own backups. |

## 5. Needed from IT

The general brief (internal domain, LAN and VPN ranges, certificate, server), plus for
InnoCalc: a service account and SMB path so the host can mount the projects share, the Entra ID
app registration for edge sign-in, and a tenant UID (`add-app.sh innocalc <uid>`, distinct from
InnoResource's).

## 6. Suggested order

1. Commit and push the three module repositories' local work, then commit the submodule
   pointers (G1), and run `python -m icm.merge --libraries` on each PC to rewrite its projects'
   files without Windows paths (G2).
2. Step 2 once IT provides the domain and ranges.
3. Step 3 with **G5 (critical)** verified inside the image and G6 minimum replacements.
4. G3 merge and **G4 (critical)** share validation on a pilot group, with Package Export and
   Verification admin-only (the default) until PDF output is proven.
5. Edge sign-in (G7), then open to all staff.
