# Docker Deployment - InnoCalc on the Shared Application Host

The runbook for moving InnoCalc from each designer's PC to one Docker tenant on the shared
Ubuntu application host, behind the shared Caddy reverse proxy (the InnoResource hosting plan,
`C:\CODING\INNORESOURCE - TS BRANCH\README - docker-instructions.md`). The detailed gap list is
in [DEPLOYMENT-GAP-ASSESSMENT.md](DEPLOYMENT-GAP-ASSESSMENT.md); the wider backlog is in
[ROADMAP.md](../ROADMAP.md).

> **Two critical steps gate go-live.** Neither can be proven on a PC. Do not open the server
> instance to staff until both are signed off below.
>
> 1. **C1 - Mount the projects drive from Linux and prove file locking across it.**
> 2. **C2 - Prove PDF printing inside the container (and on Windows).** Until then, Package
>    Export and Verification stay admin-only.

---

## Critical step C1 - projects drive mount and cross-platform file locking

**Why it is critical.** Every calculation library, revision snapshot, issued package and
verification record lives in the project folders on the projects drive, not in the
container. The server must read and write that drive, and while PCs and the server can both
reach it, their locks must exclude each other or two people can overwrite one project's index.

InnoCalc serialises every write to a project's `innocalc-library.json` with an OS lock on
`.innocalc-library.lock` beside it ([apps/manager/icm/locking.py](../apps/manager/icm/locking.py)).
**Both platforms now take the same lock: an exclusive byte-range lock on byte 0** -
`msvcrt.locking` on Windows and a POSIX record lock (`fcntl.lockf`) on Linux, which the CIFS
client forwards to the file server as an SMB byte-range lock. The file server therefore
arbitrates between PCs and the host. `flock` is no longer used (older CIFS clients keep it
local to the host). A second holder in the same process is refused too. This is the design;
the sign-off tests below prove it on the real share.

**Needs from IT**

* A service account for the host with read-write access to the projects share (read-only for
  preview), and the SMB path (`//fileserver/Projects` or equivalent).
* Agreement on the Windows path people use for the same share (`J:\Active Projects` or the
  UNC path) - this becomes `ICM_SHARE_PATH` so draft emails link to a path Outlook can open.

**Mount (host, not container)**

```
# /etc/fstab - credentials file root:root 0600, never in the repository
//fileserver/Projects  /mnt/projects  cifs  credentials=/etc/innocalc/smb.cred,uid=<tenant uid>,gid=<tenant gid>,file_mode=0660,dir_mode=0770,vers=3.1.1,cache=strict,_netdev  0 0
```

Do **not** add `nobrl` (it turns off byte-range locks sent to the file server) or
`cache=none`/`loose` without re-running the tests below.

Compose mounts host `/mnt/projects` at `/projects` (the image's `ICM_ROOT`) read-write in
`innocalc-prod` and read-only in `innocalc-preview`.

**Sign-off tests (all must pass on the real share, not a local disk)**

The lock tool holds or probes one lock file: `python -m icm.locking hold <file> [--seconds N]`
and `python -m icm.locking probe <file>` (exit 0 free, 3 held elsewhere). Run it from
`apps/manager` on a PC, or in the container with
`docker compose run --rm innocalc-prod python -m icm.locking ...`. Use a scratch file such as
`<projects root>/J0000 - LOCK TEST/.innocalc-lock-test`.

| # | Test | Pass condition |
|---|------|----------------|
| C1.1 | Host: `hold` in one container, `probe` from a second | Probe exits 3 (`busy`) while held, 0 after |
| C1.2 | PC: `hold J:\...\.innocalc-lock-test --seconds 120`; host: `probe /projects/.../.innocalc-lock-test`. Then the reverse | Probe exits 3 both ways |
| C1.3 | Save the same calculation from a PC and from the server within a second | One save succeeds, the other is told to refresh; `innocalc-library.json` is valid JSON with both or one revision, never a torn file |
| C1.4 | Rename/move a calculation's package on the server; open the project on a PC | Paths resolve (stored paths are `/`-relative, see ROADMAP "portable paths") |
| C1.5 | Kill the container mid-save | `.json.bak` present; index loads; no orphan lock prevents the next save |

**Cut-over guard.** Whether or not C1.2 passes, PCs and the server should not both write to
the same projects. Set `ICM_OWNS_PROJECTS=true` on production only: at start it writes
`.innocalc-server.json` (with the site URL from `ICM_ALLOWED_HOSTS`) into the projects root.
Any PC copy whose projects root holds that marker then refuses every write with 409 *"Projects
on this drive are now managed by the InnoCalc server at https://...; save your work there"*,
and its toolbar shows a read-only notice. Reading, calculating and printing on the PC still
work. The setting is refused on a PC or a read-only preview. Deleting the marker hands the
projects back to the PCs.

**If C1.2 fails** (Windows and Linux locks do not exclude each other) the rule is: **cut every
user over to the server at once** and retire the desktop managers the same day - the guard
above enforces it. The data-migration steps below are written for that single cut-over.

**Portable data (done in v0.0.1).** No stored path now contains a drive letter or a backslash:
projects are stored by their location under the projects root, discovery by root-relative
paths, and library, issue register and QA records by project-relative `/` paths. Older records
are rewritten on their next save, or all at once with `python -m icm.merge --libraries` run on
each PC **before** the cut-over (a PC's drive letters only resolve on that PC).
`ICM_LEGACY_ROOTS` (default `J:\Active Projects`) lets the Linux server recognise project
registry records written on a PC.

---

## Critical step C2 - PDF printing inside the container

**Why it is critical.** Saving a calculation prints its PDF; Package Export and Verification
combine, watermark and flatten PDFs. On Windows the earlier full smoke run returned from
Chromium without producing PDFs (docs/IMPLEMENTATION-STATUS.md); `python -m tooling.smoke` has
since **passed twice on one PC** (24 September, `artifacts/smoke-d2c9b009`; 25 September,
`artifacts/smoke-8f18b29a`: 3 modules saved and reopened, 12-page flattened package). Repeat
C2.1 on a second PC and complete C2.2-C2.5.

**Until C2 passes, Package Export and Verification are admin-only.** This is now the default:
a blank `ICM_TAB_ACCESS` means `package=admin,qa=admin`
([apps/manager/icm/config.py](../apps/manager/icm/config.py)). Admins are `ICM_ADMINS` plus
anyone marked `admin` in `people.json`. Open the tabs to everyone only by setting
`ICM_TAB_ACCESS=package=user,qa=user` after sign-off.

**The image** ([Dockerfile](../Dockerfile), [.dockerignore](../.dockerignore)) meets the
requirements:

* Debian `chromium`, `fonts-crosextra-carlito` (metric-compatible with Calibri, which the sheets
  fall back to from Aptos), Liberation and DejaVu, `tzdata` with `TZ=Australia/Adelaide`.
* `HOME=/tmp`, font cache under `/tmp`, a unique `--user-data-dir` per print
  (`packages/calcpad/export.py`), so it runs as any UID with a read-only root.
* `INNOCALC_BROWSER=/usr/bin/chromium` and
  `INNOCALC_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"`. **Decision:** Chromium's
  sandbox cannot start under `cap_drop: ALL` with the default seccomp profile, and it only
  prints InnoCalc's own sheets from local files with background networking disabled, so the
  container boundary is the sandbox. `/dev/shm` is 64 MB in a container, hence the second flag.
* The health check sends `Host: $ICM_HEALTH_HOST`, so compose sets `ICM_HEALTH_HOST` to the
  site's hostname.

**Automated proof (C2.2).** The `container-pdf` job in
[.github/workflows/shared-quality.yml](../.github/workflows/shared-quality.yml) builds the image
on every push and runs the full PDF smoke inside it as UID 1001 with a read-only root,
`--cap-drop ALL` and `no-new-privileges`, then starts the service, waits for Docker's health
check, asserts `pdfBrowser: true` and a 400 for a foreign `Host`. The smoke output (saved
sheets, package PDF, `report.json`) is uploaded as the `container-smoke` artifact for C2.5. It
has not run yet: it runs when the repository is pushed. Docker Desktop cannot run on the
development PC used so far (WSL is not installed and installing it needs an administrator).
Locally, once Docker works:

```
docker build -t innocalc:local .
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL -u 1001:1001 -w /app innocalc:local \
  python -m tooling.smoke --output /tmp/smoke
```

**Sign-off tests**

| # | Test | Pass condition |
|---|------|----------------|
| C2.1 | `python -m tooling.smoke` (with PDF) on a Windows PC | Every module's saved PDF exists and opens |
| C2.2 | The same inside the image (CI `container-pdf`, or `docker compose exec innocalc-preview python -m tooling.smoke --output /tmp/smoke`) | Same, and `/api/health` reports `pdfBrowser: true` |
| C2.3 | Build a package of 3 modules + an imported PDF + a drawing set | Page count equals the contents page's sheet count; contents links jump to the right sheet; watermark on every sheet; file is flattened |
| C2.4 | Create a verification package, mark it up in Bluebeam, return it | Comments import into the register |
| C2.5 | Compare one sheet printed on Windows and in the container | No reflowed page breaks or missing glyphs |

---

## Deployment steps (after C1 and C2)

1. **Source.** Clone with submodules: `git clone --recurse-submodules` (Steel, Concrete Column
   and Calculation Pad are pinned submodules, see `.gitmodules`). `python -m tooling
   release-check` refuses a release with uncommitted or unpushed module commits.
2. **Image**: [Dockerfile](../Dockerfile) - Python 3.12 slim, Chromium and fonts, `tzdata` with
   `TZ=Australia/Adelaide` (file stamps use local time), `PYTHONDONTWRITEBYTECODE=1`,
   `ICM_HOST=0.0.0.0`. Compose adds non-root `user:`, `read_only: true`, tmpfs `/tmp`.
   [.dockerignore](../.dockerignore) excludes the stale root copies `InnoCalcManager/`,
   `CalculationPad/`, `SteelMemberDesign/`, `ConcreteColumnDesign/`, Git metadata, artifacts
   and Steel's reference library.
3. **Settings** (`deploy/prod.env`, never committed): `ICM_ROOT=/projects`,
   `ICM_SHARE_PATH=\\fileserver\Projects` (or `J:\Active Projects`), `ICM_LEGACY_ROOTS`,
   `ICM_AUTH_MODE=proxy`, `ICM_TRUSTED_PROXIES`, `ICM_ALLOWED_HOSTS`, `ICM_HTTPS=true`,
   `ICM_ADMINS`, `ICM_DATA_DIR=/data`, `ICM_BACKUP_DIR=/backups`, `ICM_HEALTH_HOST`,
   `ICM_OWNS_PROJECTS=true` (from cut-over day). Preview adds `ICM_READ_ONLY=true`.
4. **Merge everyone's lists** (one combined project list and people directory). Copy each PC's
   `apps/manager/data` folder to the host, then with the prod container stopped:
   ```
   python -m icm.merge pc-jarvis/ pc-alex/ ... --into /data            # dry run: report only
   python -m icm.merge pc-jarvis/ pc-alex/ ... --into /data --apply    # backs up /data first
   ```
   Review the report: `notPortable` lists projects added from outside the projects root (they
   cannot be served; re-add them from under the root), `initialsShared` lists people sharing
   initials.
5. **Edge sign-in.** Entra ID at Caddy; the identity header is trusted only from Caddy
   (`ICM_TRUSTED_PROXIES`). Until it is live, open production to a named pilot group only.
6. **Health.** The probe must send the site's `Host` header: `GET /api/health` returns 200
   `ok`/`degraded` or 503 `unavailable`.
7. **Backups.** `docker compose exec innocalc-prod python -m icm.backup create`; preview refresh
   restores the newest prod snapshot with `python -m icm.backup restore <file> --data-dir /data
   --force` in a one-off container.
8. **Cut-over day.** Stop every desktop manager (see C1), run step 4 with the final copies,
   start prod with `ICM_OWNS_PROJECTS=true`, check `/api/health`, confirm a PC now shows the
   read-only notice, open one project per team.
