import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";

const DESCRIPTION =
  "Upload sales history, get per-SKU demand forecasts and reorder suggestions, and watch accuracy improve every week.";

export const metadata: Metadata = {
  metadataBase: new URL("https://vyaparsense.com"),
  title: {
    default: "VyaparSense — demand sensing & auto-replenishment",
    template: "%s · VyaparSense",
  },
  description: DESCRIPTION,
  applicationName: "VyaparSense",
  openGraph: {
    title: "VyaparSense — demand sensing & auto-replenishment",
    description: DESCRIPTION,
    siteName: "VyaparSense",
    type: "website",
    url: "/",
  },
  twitter: {
    card: "summary",
    title: "VyaparSense — demand sensing & auto-replenishment",
    description: DESCRIPTION,
  },
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
