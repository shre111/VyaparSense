import type { Metadata } from "next";
import Link from "next/link";
import { ForecastExplorer } from "@/components/forecast-explorer";

export const metadata: Metadata = {
  title: "Forecasts — VyaparSense",
};

export default function ForecastsPage() {
  return (
    <main className="container max-w-3xl py-16">
      <Link href="/" className="text-sm text-muted-foreground hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-3xl font-bold tracking-tight">Per-SKU forecasts</h1>
      <p className="mt-2 text-muted-foreground">
        Generate 7-day demand forecasts for a tenant&apos;s series — each picked
        by backtest — and chart any one of them.
      </p>
      <div className="mt-8">
        <ForecastExplorer />
      </div>
    </main>
  );
}
