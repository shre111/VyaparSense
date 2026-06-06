"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api";

type Mode = "login" | "signup";

export default function LoginPage() {
  const { user, loading, login, signup } = useAuth();
  const router = useRouter();
  const [mode, setMode] = React.useState<Mode>("login");
  const [tenantId, setTenantId] = React.useState("demo");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  // Already signed in? Don't show the login form — send them into the app.
  React.useEffect(() => {
    if (!loading && user !== null) router.replace("/upload");
  }, [loading, user, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await signup(tenantId.trim(), email.trim(), password);
      }
      // Land inside the app (not the marketing page) so it's clear you're in.
      router.replace("/upload");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reach the API. Is the backend running?",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="bg-hero flex min-h-screen flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-md">
      <Link
        href="/"
        className="mb-6 flex items-center justify-center gap-2 text-lg font-semibold tracking-tight"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-sm font-bold text-primary-foreground">
          V
        </span>
        VyaparSense
      </Link>
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>{mode === "login" ? "Log in" : "Create your account"}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === "login"
              ? "Welcome back to VyaparSense."
              : "Start sensing demand and automating reorders."}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {mode === "signup" && (
              <label className="flex flex-col gap-1 text-sm font-medium">
                Tenant
                <input
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  required
                  className="h-10 rounded-lg border border-input bg-card px-3 text-sm transition-colors focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                  placeholder="your-company"
                />
              </label>
            )}
            <label className="flex flex-col gap-1 text-sm font-medium">
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm transition-colors focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                placeholder="you@company.com"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === "signup" ? 8 : undefined}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className="h-10 rounded-lg border border-input bg-card px-3 text-sm transition-colors focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                placeholder={mode === "signup" ? "at least 8 characters" : "password"}
              />
            </label>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <Button type="submit" disabled={busy} className="mt-2">
              {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {mode === "login" ? "Log in" : "Sign up"}
            </Button>
          </form>

          <p className="mt-4 text-sm text-muted-foreground">
            {mode === "login" ? "No account yet? " : "Already have an account? "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setError(null);
              }}
              className="text-primary hover:underline"
            >
              {mode === "login" ? "Sign up" : "Log in"}
            </button>
          </p>
        </CardContent>
      </Card>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        <Link href="/" className="hover:underline">
          ← Back home
        </Link>
      </p>
      </div>
    </main>
  );
}
