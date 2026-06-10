import Link from "next/link";

const LINKS = [
  { href: "/login", label: "Log in" },
  { href: "/upload", label: "Upload" },
  { href: "/forecasts", label: "Forecasts" },
  { href: "/reorder", label: "Reorder" },
  { href: "/accuracy", label: "Accuracy" },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t">
      <div className="container flex flex-col items-center gap-6 py-10 sm:flex-row sm:justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-xs font-bold text-primary-foreground">
            V
          </span>
          VyaparSense
        </Link>
        <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} VyaparSense · Demand sensing &amp;
          auto-replenishment
        </p>
      </div>
    </footer>
  );
}
