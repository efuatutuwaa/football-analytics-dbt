# Football Analytics Portfolio Site

Cinematic one-page editorial portfolio for the football analytics engineering project.

Built with **Next.js**, **Tailwind CSS**, and **Framer Motion**.

Content sources (read at build time):

- [`../docs/football_analytics_story.md`](../docs/football_analytics_story.md) — main story (`/`)
- [`../docs/case-study.md`](../docs/case-study.md) — technical case study (`/case-study`)

## Run locally

```bash
cd portfolio-site
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Build

```bash
npm run build
npm start
```

## Structure

| Path | Purpose |
|------|---------|
| `src/app/page.tsx` | Single-page layout |
| `src/components/` | Reusable UI (buttons, quotes, eureka, gallery, architecture) |
| `src/data/content.ts` | Platform stats, pipeline, eureka cards |
| `src/data/links.ts` | CTA URLs and nav sections |
| `public/dashboards/` | Dashboard screenshot placeholders |

## Sections

1. Hero / Opening
2. The Idea
3. Platform Scope
4. Data Modelling
5. Ingestion Layer
6. Transformation Layer
7. Eureka Moments
8. Architecture & Pipeline
9. Dashboard Screens
10. Reflections
11. Closing / CTA

## Deploy

See **[DEPLOY.md](./DEPLOY.md)** for Vercel and GitHub Pages instructions.
