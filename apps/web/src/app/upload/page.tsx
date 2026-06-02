import type { Metadata } from "next";
import Link from "next/link";
import { RequireAuth } from "@/components/require-auth";
import { UploadForm } from "@/components/upload-form";

export const metadata: Metadata = {
  title: "Upload sales history — VyaparSense",
};

export default function UploadPage() {
  return (
    <RequireAuth>
      <main className="container max-w-2xl py-16">
      <Link href="/" className="text-sm text-muted-foreground hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-3xl font-bold tracking-tight">Upload sales history</h1>
      <p className="mt-2 text-muted-foreground">
        Upload a CSV of past sales. We clean and validate it, then classify each
        SKU&apos;s demand pattern.
      </p>
      <div className="mt-8">
        <UploadForm />
      </div>
      <p className="mt-6 text-sm text-muted-foreground">
        Uploaded some history?{" "}
        <Link href="/forecasts" className="text-primary hover:underline">
          Generate forecasts →
        </Link>
      </p>
      </main>
    </RequireAuth>
  );
}
