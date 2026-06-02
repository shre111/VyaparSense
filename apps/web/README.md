# apps/web — VyaparSense frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui.

Talks to the FastAPI backend (`apps/api`) over HTTPS. **Never** connects to the ML database directly (see [ADR-003](../../decisions.md)).

## Stack

Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS 3 with
shadcn/ui design tokens (`cn` helper, CSS variables, dark-mode ready) ·
lucide-react icons.

## Develop

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
npm run lint       # next lint (eslint flat config)
npm run typecheck  # tsc --noEmit
npm run build      # production build
```

CI runs `npm ci && npm run lint && npm run typecheck && npm run build`.

## Layout

```
src/
  app/        # App Router: layout, landing page, globals.css
  lib/        # utils (cn)
```

Forthcoming (Phase 6): CSV upload UX, per-SKU forecast chart, reorder table,
and the accuracy-over-time hero chart — wired to the `apps/api` endpoints.
