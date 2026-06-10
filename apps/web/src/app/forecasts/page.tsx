import type { Metadata } from "next";
import { LineChart } from "lucide-react";
import { ForecastExplorer } from "@/components/forecast-explorer";
import { PageHeader } from "@/components/page-header";
import { RequireAuth } from "@/components/require-auth";

export const metadata: Metadata = {
  title: "Forecasts — VyaparSense",
};

export default function ForecastsPage() {
  return (
    <RequireAuth>
      <main className="container max-w-4xl py-10">
        <PageHeader
          icon={LineChart}
          title="Per-SKU forecasts"
          description="Generate 7-day demand forecasts for your series — each picked by backtest — and chart any one of them."
        />
        <div className="mt-8">
          <ForecastExplorer />
        </div>
      </main>
    </RequireAuth>
  );
}
