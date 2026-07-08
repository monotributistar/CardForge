# CardForge deployment (Coolify + Cloudflare Tunnel)

Both the Studio (frontend) and the Core (backend) run on the Linux box
(`mono-infra`, 192.168.0.156) under **Coolify**, exposed to the internet through
a single Cloudflare **tunnel** — no public ports open on the box.

## Topology

```
Internet ──TLS──> Cloudflare edge ──tunnel──> cardforge-tunnel (container)
                                                    │ (coolify network)
                                                    ▼
                                              coolify-proxy (Traefik)
                                                    │ routes by Host header
                          ┌─────────────────────────┼─────────────────────────┐
                          ▼                          ▼                          ▼
                   studio-prod (nginx)        core-prod (uvicorn)        …dev apps
```

| Hostname                        | Branch | Coolify app  | Serves            |
| ------------------------------- | ------ | ------------ | ----------------- |
| `cardforge.minarai.xyz`         | main   | studio-prod  | Studio SPA        |
| `cardforge-core.minarai.xyz`    | main   | core-prod    | Core API (:9000)  |
| `cardforge-dev.minarai.xyz`     | dev    | studio-dev   | Studio SPA        |
| `cardforge-core-dev.minarai.xyz`| dev    | core-dev     | Core API (:9000)  |

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

Enable **auto-deploy on push** so `git push origin dev` redeploys dev and merging
to `main` redeploys prod.

## Workflow

```
dev branch  ──push──> Coolify redeploys studio-dev + core-dev  (cardforge-dev.minarai.xyz)
   │ validate
   ▼
merge → main ──push──> Coolify redeploys studio-prod + core-prod (cardforge.minarai.xyz)
```
