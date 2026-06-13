import type { Metadata } from "next";
import Link from "next/link";
import { Upload } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { RequireAuth } from "@/components/require-auth";
import { UploadForm } from "@/components/upload-form";

export const metadata: Metadata = {
  title: "Upload sales history",
};

export default function UploadPage() {
  return (
    <RequireAuth>
      <main className="container max-w-3xl py-10">
        <PageHeader
          icon={Upload}
          title="Upload sales history"
          description="Upload a CSV of past sales. We clean and validate it, then classify each SKU's demand pattern."
        />
        <div className="mt-8">
          <UploadForm />
        </div>
        <p className="mt-6 text-sm text-muted-foreground">
          Uploaded some history?{" "}
          <Link href="/forecasts" className="font-medium text-primary hover:underline">
            Generate forecasts →
          </Link>
        </p>
      </main>
    </RequireAuth>
  );
}
