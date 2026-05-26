# Deploying the portfolio site

Two options. **Vercel** gives a clean URL (`your-project.vercel.app`). **GitHub Pages** is free and lives under your repo.

---

## Option A — Vercel (recommended)

1. Push this repo to GitHub.
2. Sign in at [vercel.com](https://vercel.com) → **Add New Project** → import `football-analytics-dbt`.
3. Set **Root Directory** to `portfolio-site`.
4. Leave build settings as detected (`npm run build`).
5. Deploy.

`vercel.json` in this folder configures the build. Every push to `main` that touches `portfolio-site/`, `docs/football_analytics_story.md`, or `docs/case-study.md` can auto-deploy if you enable Git integration.

**Custom domain:** Vercel project → Settings → Domains.

No `basePath` — the site is served from the domain root.

---

## Option B — GitHub Pages

1. Push to GitHub.
2. Repo **Settings → Pages → Build and deployment**
   - Source: **GitHub Actions**
3. Push to `main` (or run the **Deploy portfolio site** workflow manually).

The workflow [`.github/workflows/deploy-portfolio.yml`](../.github/workflows/deploy-portfolio.yml) builds a static export and publishes it.

**Live URL (default):**

`https://<your-github-username>.github.io/football-analytics-dbt/`

The build sets `GITHUB_PAGES=true`, which enables `output: 'export'` and `basePath: '/football-analytics-dbt'` in `next.config.ts`.

---

## Local production build

```bash
cd portfolio-site
npm run build
npm start          # Vercel-style (Node server)

# GitHub Pages preview:
GITHUB_PAGES=true npm run build
npx serve out -p 3000
# → http://localhost:3000/football-analytics-dbt/
```

---

## Content updates

Edit [`../docs/football_analytics_story.md`](../docs/football_analytics_story.md) (main story) or [`../docs/case-study.md`](../docs/case-study.md) (technical appendix), push to `main`, and wait for the deploy to finish.
