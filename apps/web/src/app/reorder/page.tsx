import type { Metadata } from "next";
import Link from "next/link";
import { ReorderTable } from "@/components/reorder-table";
import { RequireAuth } from "@/components/require-auth";

export const metadata: Metadata = {
  title: "Reorder suggestions — VyaparSense",
};

export default function ReorderPage() {
  return (
    <RequireAuth>
      <main className="container max-w-4xl py-16">
        <Link href="/" className="text-sm text-muted-foreground hover:underline">
          ← Back
        </Link>
        <h1 className="mt-4 text-3xl font-bold tracking-tight">Reorder suggestions</h1>
        <p className="mt-2 text-muted-foreground">
          Service-level reorder points and order quantities per SKU, from each
          series&apos; demand forecast. Tune lead time, service level, and on-hand
          stock.
        </p>
        <div className="mt-8">
          <ReorderTable />
        </div>
      </main>
    </RequireAuth>
  );
}
