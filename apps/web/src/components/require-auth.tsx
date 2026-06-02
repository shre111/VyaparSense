"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

/**
 * Gate a protected page on an authenticated session. While the session is being
 * restored it shows a spinner; if unauthenticated it redirects to `/login`.
 * Renders a small header (tenant + logout) above the protected content.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!loading && user === null) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden />
      </div>
    );
  }

  if (user === null) {
    return null; // redirecting
  }

  return (
    <>
      <header className="border-b">
        <div className="container flex items-center justify-between py-3">
          <Link href="/" className="font-semibold">
            VyaparSense
          </Link>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>
              {user.email} · {user.tenant_id}
            </span>
            <Button variant="outline" size="sm" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
