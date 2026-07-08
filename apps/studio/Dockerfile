# CardForge Studio — static SPA served by nginx.
# Build context is the REPO ROOT (pnpm workspace), Dockerfile path apps/studio/Dockerfile.
#   docker build -f apps/studio/Dockerfile --build-arg VITE_CORE_URL=https://cardforge-core.minarai.xyz -t cardforge-studio .
#
# VITE_CORE_URL is baked in at BUILD time (Vite inlines import.meta.env), so
# each environment (prod/dev) builds its own image pointing at its own Core.

FROM node:20-slim AS build
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
WORKDIR /app

# Dependency layer — cached until a manifest or the lockfile changes.
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY apps/studio/package.json apps/studio/package.json
RUN pnpm install --frozen-lockfile

# Build the SPA.
COPY . .
ARG VITE_CORE_URL=http://localhost:9000
ENV VITE_CORE_URL=${VITE_CORE_URL}
RUN pnpm --filter @cardforge/studio build

FROM nginx:1.27-alpine AS runtime
COPY apps/studio/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/studio/dist /usr/share/nginx/html
EXPOSE 80
