# CardForge deployment (Coolify + Cloudflare Tunnel)

Both the Studio (frontend) and the Core (backend) run on the Linux box
(`mono-infra`, 192.168.0.156) under **Coolify**, exposed to the internet through
a single Cloudflare **tunnel** — no public ports open on the box.

## Topology

```
Internet ──TLS──> Cloudflare edge ──tunnel──> cardforge-tunnel (container)
                                                    │ (coolify network)
                      ┌─────────────────────────────┴───────────┐
                      ▼                                         ▼
                coolify-proxy (Traefik)              coolify:8080 (control plane)
                      │ routes by Host header          ONLY /webhooks/…/manual
   ┌──────────────────┼──────────────────┐             everything else 404s
   ▼                  ▼                  ▼
studio-prod      core-prod          …dev apps
```

| Hostname                        | Branch | Coolify app  | Serves            |
| ------------------------------- | ------ | ------------ | ----------------- |
| `cardforge.minarai.xyz`         | main   | studio-prod  | Studio SPA        |
| `cardforge-core.minarai.xyz`    | main   | core-prod    | Core API (:9000)  |
| `cardforge-dev.minarai.xyz`     | dev    | studio-dev   | Studio SPA        |
| `cardforge-core-dev.minarai.xyz`| dev    | core-dev     | Core API (:9000)  |
| `cardforge-hooks.minarai.xyz`   | —      | (Coolify)    | deploy webhook only |

Coolify application UUIDs (needed for the API and for reading the deployment
queue):

| App         | id | UUID                       |
| ----------- | -- | -------------------------- |
| core-dev    | 1  | `j1qg2mht4qilwfr30bxtp5q4` |
| core-prod   | 2  | `fnbjrqr3ov84ytre85pd08zj` |
| studio-dev  | 3  | `lhwo6bdor097r4f88kyv7oco` |
| studio-prod | 4  | `y11eghqmxin8vm1bb1m540my` |

The Studio bakes `VITE_CORE_URL` in at **build time**, so each Studio app points
at its own-environment Core:
- studio-prod → `https://cardforge-core.minarai.xyz`
- studio-dev  → `https://cardforge-core-dev.minarai.xyz`

## Images

- **Core**: `/Dockerfile` (FastAPI + manifold3d, uvicorn on :9000).
- **Studio**: `/apps/studio/Dockerfile` (pnpm build → nginx static, :80).
  Build context is the repo root; pass `VITE_CORE_URL` as a build arg.

## Tunnel (one-time, already done)

Tunnel `cardforge` = `86d2721e-ac76-4fbd-b301-6cf130c644ba`, created from the
Mac's authenticated `cloudflared`. DNS routes (proxied CNAMEs → the tunnel):

```
cloudflared tunnel route dns --overwrite-dns 86d2721e-ac76-4fbd-b301-6cf130c644ba cardforge-dev.minarai.xyz
cloudflared tunnel route dns --overwrite-dns 86d2721e-ac76-4fbd-b301-6cf130c644ba cardforge-core-dev.minarai.xyz
# Production names flipped off the old Worker/Mac tunnel only after dev is validated:
# cloudflared tunnel route dns --overwrite-dns 86d2721e… cardforge.minarai.xyz
# cloudflared tunnel route dns --overwrite-dns 86d2721e… cardforge-core.minarai.xyz
```

The tunnel runs as a standalone container on the box (see
`deploy/cloudflared/docker-compose.yml`). The credential file is a secret and is
**not** in git:

```bash
# From the Mac, copy the tunnel credentials to the box:
scp ~/.cloudflared/86d2721e-ac76-4fbd-b301-6cf130c644ba.json \
    monotributistar@192.168.0.156:~/cardforge/deploy/cloudflared/credentials.json
# On the box:
cd ~/cardforge && docker compose -f deploy/cloudflared/docker-compose.yml up -d
```

## Coolify apps (create these 4)

For each app in the Coolify UI (Project → Environment → **+ New Resource →
Public/Private Repository**, repo `monotributistar/CardForge`):

### core-prod / core-dev
- Branch: `main` / `dev`
- Build pack: **Dockerfile**, location `/Dockerfile`
- Port: `9000`
- Domain: `http://cardforge-core.minarai.xyz` / `http://cardforge-core-dev.minarai.xyz`
  (use `http://` — TLS is at the Cloudflare edge, so disable Coolify's HTTPS/Let's Encrypt for these)

### studio-prod / studio-dev
- Branch: `main` / `dev`
- Build pack: **Dockerfile**, location `/apps/studio/Dockerfile`, build context `/`
- Build arg: `VITE_CORE_URL=https://cardforge-core.minarai.xyz`
  (dev: `https://cardforge-core-dev.minarai.xyz`)
- Port: `80`
- Domain: `http://cardforge.minarai.xyz` / `http://cardforge-dev.minarai.xyz`

## Auto-deploy on push

Coolify only deploys when something tells it to. It is on the LAN, so GitHub
cannot reach it directly — the tunnel publishes **one path** for that, and
nothing else of the control plane:

```yaml
# deploy/cloudflared/config.yml
- hostname: cardforge-hooks.minarai.xyz
  path: ^/webhooks/source/github/events/manual$   # unanchored regex → anchor it
  service: http://coolify:8080                    # the app container, not Traefik
- hostname: cardforge-hooks.minarai.xyz
  service: http_status:404                        # /login, /api/v1/* … never arrive
```

Each application authenticates its own deliveries with its own HMAC secret
(`applications.manual_webhook_secret_github`), and Coolify verifies the
signature per application. One shared webhook would therefore only ever deploy
one app — so the repo carries **four** webhooks, one per app, each posting to
the same URL with that app's secret:

```bash
# The secret Coolify expects for app <id> (never commit or paste it elsewhere):
ssh monotributistar@192.168.0.156 \
  'docker exec coolify php artisan tinker \
     --execute="echo \App\\Models\\Application::find(<id>)->manual_webhook_secret_github;"'

# Register it (repeat per app; GitHub → Settings → Webhooks shows the result):
gh api repos/monotributistar/CardForge/hooks -X POST --input - <<< '{
  "name":"web","active":true,"events":["push"],
  "config":{"url":"https://cardforge-hooks.minarai.xyz/webhooks/source/github/events/manual",
            "content_type":"json","secret":"…","insecure_ssl":"0"}}'
```

A push delivers to all four; each app deploys if the branch matches and the
signature verifies, and the other deliveries answer `Nothing to do.` — the
`Invalid signature` lines in a delivery's response are that mechanism working,
not a fault.

### Security posture

- **The control plane is not published.** Coolify can start containers on this
  box, so treat its UI as root. Reach it over the LAN/VPN
  (`http://192.168.0.156:8000`), never through the tunnel.
- **The webhook secret is the only thing between the internet and a build.**
  Anyone who can forge a valid signature can make the box build and run a
  branch. Rotate in Coolify (and re-register) if one is ever exposed.
- **A build runs repo code on the box.** Whoever can push can execute there —
  so branch protection on `main` is a deployment control, not just hygiene.
- **Worth adding:** a Cloudflare WAF rule on `cardforge-hooks.minarai.xyz`
  allowing only GitHub's published hook ranges (`api.github.com/meta` →
  `.hooks`), plus rate limiting. The signature check already gates it; this
  keeps unauthenticated traffic away from the endpoint entirely.
- `credentials.json` (the tunnel secret) stays out of git — see above.

### Manual deploy (no push)

```bash
# Coolify UI → app → Redeploy, or with an API token (Keys & Tokens → API tokens):
curl -X POST 'http://192.168.0.156:8000/api/v1/deploy?uuid=<app-uuid>' \
     -H 'Authorization: Bearer <token>'
```

## Workflow

```
dev branch  ──push──> Coolify redeploys studio-dev + core-dev  (cardforge-dev.minarai.xyz)
   │ validate
   ▼
merge → main ──push──> Coolify redeploys studio-prod + core-prod (cardforge.minarai.xyz)
```

Watch a deployment:

```bash
ssh monotributistar@192.168.0.156 \
  'docker exec coolify-db psql -U coolify -d coolify -At \
     -c "select application_name,status from application_deployment_queues \
         order by created_at desc limit 4;"'
```

## Changing the tunnel

`docker kill -s HUP cardforge-tunnel` does **not** reload the config — this
cloudflared exits on SIGHUP and takes every public hostname down with it.
Validate first, then restart properly:

```bash
cd ~/cardforge/deploy/cloudflared
docker run --rm -v "$PWD/config.yml:/etc/cloudflared/config.yml:ro" \
  --entrypoint cloudflared cloudflare/cloudflared:2026.7.0 \
  --config /etc/cloudflared/config.yml tunnel ingress validate
# and check where a URL actually lands:
#   … tunnel ingress rule https://cardforge-hooks.minarai.xyz/login
docker compose -f deploy/cloudflared/docker-compose.yml up -d
```
