import type { Metadata } from "next";
import Link from "next/link";
import { AccuracyHero } from "@/components/accuracy-hero";
import { RequireAuth } from "@/components/require-auth";

export const metadata: Metadata = {
  title: "Accuracy over time — VyaparSense",
};

export default function AccuracyPage() {
  return (
    <RequireAuth>
      <main className="container max-w-4xl py-16">
        <Link href="/" className="text-sm text-muted-foreground hover:underline">
          ← Back
        </Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight">
          Getting smarter over time
        </h1>
        <p className="mt-2 text-muted-foreground">
          Rolling forecast accuracy (WAPE) week over week, and the inventory KPIs a
          forecast-driven reorder policy delivers versus a naive one.
        </p>
        <div className="mt-8">
          <AccuracyHero />
        </div>
      </main>
    </RequireAuth>
  );
}
