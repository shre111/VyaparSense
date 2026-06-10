import Link from "next/link";
import { LineChart, PackageCheck, TrendingDown, Upload } from "lucide-react";
import { AccuracyDemo } from "@/components/accuracy-demo";
import { GetStartedButton } from "@/components/get-started-button";
import { SiteFooter } from "@/components/site-footer";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    icon: Upload,
    title: "Upload sales history",
    body: "Drop a CSV of past sales. We clean it, validate it, and classify each SKU's demand pattern.",
  },
  {
    icon: LineChart,
    title: "Forecast per SKU",
    body: "Per-series models are picked by backtest — from honest baselines to a global LightGBM champion.",
  },
  {
    icon: PackageCheck,
    title: "Reorder with confidence",
    body: "Service-level reorder points, safety stock, and order quantities — not guesswork.",
  },
];

// The model "depth ladder": each rung must beat the previous on a fixed backtest.
const LADDER = [
  "Naive / moving-average / seasonal baselines — the permanent benchmark",
  "Classical time-series: ETS and AutoARIMA",
  "Intermittent & probabilistic: Croston / SBA / TSB, quantile forecasts",
  "Global LightGBM trained across every SKU and store",
  "Hierarchical reconciliation so store and SKU forecasts stay coherent",
  "Transfer-learning cold-start for brand-new SKUs",
];

function StepCard({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Upload;
  title: string;
  body: string;
}) {
  return (
    <div className="group rounded-xl border bg-card p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

export default function Home() {
  return (
    <>
      <main className="container py-16">
      {/* Hero */}
      <section className="bg-hero -mx-4 mb-4 rounded-3xl px-4 py-10">
        <div className="mx-auto max-w-3xl text-center">
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 shadow-sm",
              "text-xs font-medium text-muted-foreground",
            )}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            Demand sensing &amp; auto-replenishment
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-5xl">
            Stop guessing inventory.
            <br />
            <span className="text-gradient">Start sensing demand.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            VyaparSense learns your demand and tells you exactly what to reorder —
            and it gets measurably smarter every week.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <GetStartedButton />
            <Link
              href="#smarter"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              See how it works
            </Link>
          </div>
        </div>
      </section>

      {/* Getting smarter — the signature story */}
      <section id="smarter" className="mx-auto mt-20 max-w-4xl scroll-mt-16">
        <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
          <h2 className="text-2xl font-bold tracking-tight">
            It gets measurably smarter every week
          </h2>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Every actual sale becomes a training label. We persist every forecast
            and later score it against what really happened, so rolling accuracy
            (WAPE) is reconstructable — and visibly improves as the model learns.
          </p>
          <div className="mt-6">
            <AccuracyDemo />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Illustrative. Your real curve is reconstructed from stored
            forecast-vs-actual history on the Accuracy page.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto mt-20 max-w-5xl">
        <h2 className="text-center text-2xl font-bold tracking-tight">How it works</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step) => (
            <StepCard key={step.title} {...step} />
          ))}
        </div>
      </section>

      {/* Proof / business impact */}
      <section className="mx-auto mt-20 max-w-4xl">
        <div className="bg-hero flex flex-col items-center gap-3 rounded-2xl border p-8 text-center shadow-sm">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
            <TrendingDown className="h-7 w-7" aria-hidden />
          </span>
          <p className="text-3xl font-bold">
            91% &rarr; <span className="text-gradient">97.5%</span> fill rate
          </p>
          <p className="max-w-xl text-sm text-muted-foreground">
            In a day-by-day policy simulation on sample data (95% service level),
            forecast-driven reordering lifted fill rate from 91% to 97.5% — about
            73% fewer lost units, without piling on dead stock.
          </p>
        </div>
      </section>

      {/* Under the hood — the depth ladder */}
      <section className="mx-auto mt-20 max-w-3xl">
        <h2 className="text-2xl font-bold tracking-tight">Under the hood</h2>
        <p className="mt-2 text-muted-foreground">
          A model &ldquo;depth ladder&rdquo; — each rung has to beat the previous
          one on the same backtest before it earns its place. A naive model
          winning for a given SKU is a valid, expected outcome.
        </p>
        <ol className="mt-6 space-y-3">
          {LADDER.map((rung, i) => (
            <li
              key={rung}
              className="flex items-start gap-3 rounded-lg border bg-card p-3 shadow-sm"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                {i + 1}
              </span>
              <span className="text-sm">{rung}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* Footer CTA */}
      <section className="mx-auto mt-20 max-w-3xl text-center">
        <h2 className="text-2xl font-bold tracking-tight">Ready to stop guessing?</h2>
        <div className="mt-6">
          <GetStartedButton />
        </div>
      </section>
      </main>
      <SiteFooter />
    </>
  );
}
