import type { Metadata } from "next";
import { TrendingUp } from "lucide-react";
import { AccuracyHero } from "@/components/accuracy-hero";
import { PageHeader } from "@/components/page-header";
import { RequireAuth } from "@/components/require-auth";

export const metadata: Metadata = {
  title: "Accuracy over time — VyaparSense",
};

export default function AccuracyPage() {
  return (
    <RequireAuth>
      <main className="container max-w-5xl py-10">
        <PageHeader
          icon={TrendingUp}
          title="Getting smarter over time"
          description="Rolling forecast accuracy (WAPE) week over week, and the inventory KPIs a forecast-driven reorder policy delivers versus a naive one."
        />
        <div className="mt-8">
          <AccuracyHero />
        </div>
      </main>
    </RequireAuth>
  );
}
