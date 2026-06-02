import Link from "next/link";
import { LineChart, PackageCheck, Upload } from "lucide-react";
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
    <div className="rounded-lg border bg-background p-6">
      <Icon className="h-6 w-6 text-primary" aria-hidden />
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

export default function Home() {
  return (
    <main className="container py-16">
      <section className="mx-auto max-w-3xl text-center">
        <span
          className={cn(
            "inline-block rounded-full border px-3 py-1",
            "text-xs font-medium text-muted-foreground",
          )}
        >
          Demand sensing &amp; auto-replenishment
        </span>
        <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-5xl">
          Stop guessing inventory.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          VyaparSense learns your demand and tells you exactly what to reorder —
          and it gets measurably smarter every week.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/login" className={cn(buttonVariants())}>
            Get started
          </Link>
          <Link href="/upload" className={cn(buttonVariants({ variant: "outline" }))}>
            Upload sales history
          </Link>
          <Link href="/accuracy" className={cn(buttonVariants({ variant: "outline" }))}>
            Accuracy over time
          </Link>
          <Link href="/forecasts" className={cn(buttonVariants({ variant: "outline" }))}>
            View forecasts
          </Link>
          <Link href="/reorder" className={cn(buttonVariants({ variant: "outline" }))}>
            Reorder suggestions
          </Link>
        </div>
      </section>

      <section className="mx-auto mt-16 grid max-w-5xl gap-6 sm:grid-cols-3">
        {STEPS.map((step) => (
          <StepCard key={step.title} {...step} />
        ))}
      </section>
    </main>
  );
}
