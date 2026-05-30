# Plan — Demand-Sensing & Auto-Replenishment

> Codename `kirana-demand` · working brand **Restock**. This is the living roadmap: technical build, business case, profitability, and go-to-market. Numbers cited are grounded in 2025 market research (sources at bottom).

---

## 0. Thesis in one paragraph

SMB retailers and D2C brands lose money on both ends of inventory — dead stock ties up cash while stockouts lose sales — because they forecast by gut. We ingest sales history, forecast per-SKU demand (starting dumb, getting measurably smarter), and turn forecasts into concrete reorder suggestions. Every real sale is a free training label, so accuracy improves week over week. That improvement is simultaneously the customer's ROI and our defensible moat (cross-store demand data → similar-store cold-start nobody else can match).

---

## 1. Market & opportunity (grounded)

- **India kirana:** ~13M neighbourhood stores; India retail heading to **$1.4T by 2027** (Bain) and **~$2.6T by 2033 at ~9.5% CAGR** (Astute Analytica). Kiranas are under pressure from quick-commerce (~35k closures reported) → strong incentive to modernize operations.
- **India D2C:** D2C eCommerce **~$87.5B in 2025**, crossing **₹8.7 lakh cr (~$100B)**, projected to **~$322B by 2031 at ~24% CAGR** (Mordor). ~11,000 D2C companies (~800 funded). Tier-2/3 cities drive ~66% of new orders (FY26). Digital-native, clean data, willing to adopt tools — our best wedge.
- **Global tailwind:** Inventory management software market **~$3.2–3.6B (2024/25) → ~$4.8–7.1B by 2030–33 at ~8.5–11% CAGR**; SaaS is ~62% of it and SMB inquiries grew ~34% YoY (2024). AI/ML demand forecasting is the stated growth driver.
- **Why now:** cheap cloud ML, GBM models that win on retail data shape (M5), and a wave of SMBs digitizing sales (POS, Shopify, quick-commerce dashboards) that finally produces the sales history we need as input.

**Segments, in priority order:**
1. **D2C brands (India + global)** — already have clean digital sales data (Shopify/WooCommerce), feel stockouts acutely, pay in USD/₹ for tools. *Easiest wedge, fastest data.*
2. **Organized SMB retail / multi-outlet kiranas** — have POS/billing data, multiple SKUs, real reorder pain.
3. **Long tail single kiranas** — huge TAM, hardest to monetize/onboard; reach later via partners/distributors.

**TAM/SAM/SOM (illustrative, to refine):** TAM = global SMB inventory + demand-planning spend (multi-$B). SAM = digitized SMB retailers + D2C brands with usable sales history. SOM (3-yr realistic for a solo→small team) = low thousands of paying SMBs.

---

## 2. Competitive landscape & wedge

| Player | Position | Gap we exploit |
|---|---|---|
| Zoho Inventory (free tier → ~$359/mo billed annually for higher plans) | Broad inventory ops | Deep forecasting needs Zoho Analytics add-on; not ML-first |
| inFlow (~$129/mo+ for 2 users) | SMB inventory/ops | Reorder points but weak ML forecasting; scales pricey |
| Cin7 (~$349/mo+, ForesightAI module) | Mid-market/enterprise | AI forecasting exists but heavy & expensive — overkill for SMB |
| Dedicated demand planning ($500–$10k+/mo) | Enterprise forecasting | Out of SMB reach; complex |
| Spreadsheets | Status quo | No learning, no probabilistic reorder |

**Our wedge:** *forecasting-first, ML-native, SMB-priced, visibly improving.* We don't try to be a full ERP. We do the one thing those tools do worst — accurate, learning demand forecasts + reorder math — and integrate with the inventory tools they already use. **Moat:** granular cross-store demand data enabling similar-store cold-start (network effect) + the trust built by transparently showing accuracy improve.

---

## 3. Product surface (MVP → V1)

**Solo MVP (the portfolio-ready core):**
1. Upload sales history (CSV; later Shopify/CSV templates).
2. Auto-clean + validate + classify demand pattern (smooth/intermittent/erratic/lumpy via ADI & CV²).
3. Backtest baselines vs. better models per SKU; pick best by WAPE.
4. Forecast view: per-SKU demand with confidence band.
5. Reorder suggestions: reorder point, safety stock, suggested order qty, "days of cover."
6. **Accuracy-over-time chart** (rolling WAPE) — the "getting smarter" hero visual.

**V1 additions:** auth + multi-tenant, integrations (Shopify/WooCommerce/CSV scheduler), email/WhatsApp reorder alerts, hierarchical (store→category→SKU) views, exportable purchase orders, per-SKU service-level targets.

---

## 4. Technical architecture (summary)

```
[Next.js/TS]  ──HTTPS──>  [FastAPI]  ──>  [Postgres]
   (Vercel)                  │              (Neon/Supabase)
                             ├──> [Redis + Worker]  (forecast/backtest jobs)
                             └──> [packages/ml]     (forecasting + replenishment)
                                       │
                                  [S3/R2]  (CSV uploads, model artifacts, model cards)
```
- Next.js never touches the ML DB directly (ADR-003).
- Forecasts/backtests are async jobs (ADR-007).
- All forecasts persisted append-only for the flywheel chart (ADR-008).
- Multi-tenant (`tenant_id` everywhere) from day one (ADR-006).

ML pipeline: `ingest → validate → clean → classify → feature-engineer → backtest/select → forecast → reorder-calc → persist`.

---

## 5. Build phases (each = a milestone of micro-issues/PRs)

> Every phase ships something demoable. Conventions per [CLAUDE.md](CLAUDE.md) §6.

### Phase 0 — Foundations
- Monorepo scaffold (`apps/web`, `apps/api`, `packages/ml`), docker-compose, CI (ruff/mypy/pytest, eslint/tsc/vitest), pre-commit, issue/PR templates, sample dataset under `data/samples/`.

### Phase 1 — Data spine
- CSV ingest + schema validation, cleaning, demand classification (ADI/CV²), Postgres schema (append-only forecasts), Alembic migrations.

### Phase 2 — Dumb baselines (the honest floor)
- Naive / moving-average / seasonal-naive + backtesting harness + WAPE/MASE/bias metrics. **This is the deliberately "dumb" baseline the demo improves on.**

### Phase 3 — Classical & intermittent
- ETS/ARIMA via `statsforecast`; Croston/SBA/TSB for sparse SKUs; per-series model selection by backtest; quantile/probabilistic forecasts.

### Phase 4 — Global ML model
- LightGBM global model (calendar/price/promo/lag/rolling features, recursive multi-step). Beat Phase 3 on the fixed backtest or document why not.

### Phase 5 — Replenishment engine
- Safety stock, reorder point, EOQ, service-level targets → reorder suggestions + days-of-cover + simulated stockout/dead-stock KPIs.

### Phase 6 — Frontend product
- Upload UX, forecast charts, reorder table, **accuracy-over-time hero chart**, job-status UX.

### Phase 7 — Multi-tenant SaaS
- Auth, tenancy isolation, billing (Stripe/Razorpay), free tier limits, integrations (Shopify/WooCommerce/CSV scheduler), alerts (email/WhatsApp).

### Phase 8 — Moat features
- Hierarchical reconciliation; transfer-learning cold-start (new store/SKU borrows from similar series); similar-store network effect.

### Phase 9 — Polish & launch
- Onboarding, docs, landing page, public "MAPE dropping" demo, model cards, observability, error budgets.

---

## 6. Business model & pricing

**Model:** Freemium → tiered SaaS (land-and-expand). The free tier is also the data-moat engine (more series → better cold-start for everyone).

| Tier | India (₹/mo) | Global (USD/mo) | Limits |
|---|---|---|---|
| Free | ₹0 | $0 | 1 store, ~50–100 SKUs, weekly forecast, manual upload |
| Starter | ₹499–999 | $19–29 | 1 store, 500 SKUs, daily forecast, reorder suggestions |
| Growth | ₹2,499–4,999 | $49–99 | multi-store, 5k SKUs, integrations, alerts, hierarchy |
| Pro/Brand | ₹9,999+ | $149–299 | high SKU count, API, service-level optimization, priority |

Anchored well below inFlow (~$129/mo), Zoho's higher plans (~$359/mo annual), and Cin7 (~$349/mo) for the value delivered (forecasting-first, not full ERP). Add-ons later: WhatsApp ordering, supplier integrations, multi-channel.

**Unit economics (illustrative target):**
- Infra cost/active tenant: low (shared global model, batch jobs) — aim < $1–3/mo at small scale.
- Target gross margin: 80%+ (typical SaaS).
- CAC: content/SEO + integration-marketplace led (low) for self-serve; higher for sales-assisted multi-store.
- Payback: < 6 months on Growth tier is the goal.

**Profitability path:** solo/lean → near-zero burn (Vercel/Neon/Render free-low tiers cover MVP). Break-even is a few dozen Growth-tier customers given low infra + no payroll. Real profitability scales with self-serve conversion off the free tier; the cross-store data makes each new cohort cheaper to serve well.

---

## 7. Go-to-market & marketing

**Positioning line:** "Stop guessing inventory. Restock learns your demand and tells you exactly what to reorder — and it gets smarter every week."

**Channels:**
1. **Build-in-public / portfolio flywheel** — ship the "MAPE dropping over time" demo publicly (X/LinkedIn, blog, GitHub). The improving-accuracy chart is inherently shareable and doubles as your engineering portfolio proof.
2. **Integration marketplaces** — Shopify App Store, WooCommerce — high-intent SMB/D2C distribution where buyers already feel the pain.
3. **Content/SEO** — "how to forecast demand for [niche]", "reduce dead stock", intermittent-demand explainers; rank for SMB inventory queries.
4. **India ground game** — D2C communities, distributor/POS partnerships for kiranas (reach the long tail via whoever already sells them software/credit).
5. **Templated free tool** — a free "upload CSV → see your forecast accuracy" lead magnet that needs no signup; converts to free tier.

**Wedge sequence:** D2C (clean data, USD willingness) → multi-store SMB → kirana long tail via partners. Prove ROI with a before/after case study (dead stock ↓, stockouts ↓) early.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Garbage-in sales data | Strong validation/cleaning + clear templates + classification before forecasting |
| Fancy model doesn't beat naive | That's fine and expected per-SKU; select by backtest, keep baselines, report honestly |
| SMBs won't pay / low ARPU (esp. kirana) | Lead with D2C/global USD revenue; reach kirana via partners later |
| Forecasts wrong → trust lost | Probabilistic forecasts + transparent accuracy chart + conservative reorder defaults |
| Incumbents add forecasting | Stay forecasting-first + own the cross-store data moat + integrate, don't compete on ERP breadth |
| Cold-start (new tenant, no history) | Transfer learning from similar series — turns the moat into onboarding value |

---

## 9. Definition of done for "portfolio-grade"

- Live on a domain with a working free tier.
- Public demo where forecast accuracy visibly improves over weeks.
- Clean monorepo, CI green, ADRs + model cards, micro-PR history.
- A written case study: real/seeded dataset → dead-stock & stockout reduction.

---

## Sources (2025–26 research)
- **India kirana/retail:** ~13M kirana stores; unorganized retail ~88% of market; ~90% of FMCG via kirana; India retail ~$1.1–1.3T by 2025 → larger by 2030. ([Invest India](https://www.investindia.gov.in/team-india-blogs/modernization-kirana-stores-india), [CB Insights](https://www.cbinsights.com/research/kirana-store-india-retail/), [Statista](https://www.statista.com/statistics/935872/india-retail-market-size/))
- **India D2C:** ~$87.5B (2025), ~$322B by 2031 @ ~24% CAGR; ~11,000 D2C cos (~800 funded); Tier-2/3 = ~66% of new orders FY26. ([Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/india-d2c-ecommerce-market), [Statista](https://www.statista.com/topics/9783/d2c-market-in-india/), [Indian Retailer](https://www.indianretailer.com/article/d2c-new-commerce/trends/how-800-d2c-brands-are-shaking-indias-retail))
- **Inventory software market:** ~$3.2B (2025) → ~$4.78B by 2030 @ ~8.56% CAGR (Mordor); ~$3.58B (2024) → ~$7.14B by 2033 @ 8.4% (Grand View); SaaS ~62% share, SMB inquiries +34% YoY. ([Mordor](https://www.mordorintelligence.com/industry-reports/inventory-management-software-market), [Grand View](https://www.grandviewresearch.com/industry-analysis/inventory-management-software-market-report))
- **Competitor pricing:** inFlow ~$129/mo (2 users); Cin7 ~$349/mo (ForesightAI); Zoho Inventory free tier → ~$359/mo for higher plans (billed annually). ([Zoho pricing](https://www.zoho.com/us/inventory/pricing/), [Cin7](https://www.cin7.com/blog/best-inventory-control-software/), [Prediko](https://www.prediko.io/forecasting-demand-planning/inventory-planning-software))
- **ML approach:** M5 (Walmart, 30,490 daily series) — LightGBM + global models dominate retail data shape; Nixtla `statsforecast` for classical/intermittent (Croston/SBA/TSB; SBA usually beats Croston, TSB handles obsolescence). All Croston variants give flat forecasts → combine with temporal aggregation/GBM for trend+seasonality. ([Nixtla statsforecast](https://github.com/Nixtla/statsforecast), [Nixtla mlforecast](https://github.com/Nixtla/mlforecast), [Croston/SBA/TSB review](https://metricgate.com/docs/demand-forecasting-croston-extended/))
