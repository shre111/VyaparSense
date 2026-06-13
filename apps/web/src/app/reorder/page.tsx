import type { Metadata } from "next";
import { PackageCheck } from "lucide-react";
import { ReorderTable } from "@/components/reorder-table";
import { PageHeader } from "@/components/page-header";
import { RequireAuth } from "@/components/require-auth";

export const metadata: Metadata = {
  title: "Reorder suggestions",
};

export default function ReorderPage() {
  return (
    <RequireAuth>
      <main className="container max-w-5xl py-10">
        <PageHeader
          icon={PackageCheck}
          title="Reorder suggestions"
          description="Service-level reorder points and order quantities per SKU, from each series' demand forecast. Tune lead time, service level, and on-hand stock."
        />
        <div className="mt-8">
          <ReorderTable />
        </div>
      </main>
    </RequireAuth>
  );
}
