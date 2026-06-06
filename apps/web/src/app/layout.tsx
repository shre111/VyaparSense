import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";

export const metadata: Metadata = {
  title: "VyaparSense — demand sensing & auto-replenishment",
  description:
    "Upload sales history, get per-SKU demand forecasts and reorder suggestions, and watch accuracy improve every week.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: some browser extensions inject attributes onto
    // <html>/<body> before React hydrates (e.g. inject_vt_svd), which would
    // otherwise trip a hydration mismatch. This only suppresses attribute
    // mismatches on these two elements, not anywhere else in the tree.
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
