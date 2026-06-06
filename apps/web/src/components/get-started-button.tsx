"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Auth-aware primary CTA for the landing page. Logged out → "Get started"
 * (`/login`); logged in → "Go to the app" (`/upload`), so a signed-in visitor
 * isn't bounced back to the login form.
 *
 * While the session is still being restored we show the logged-out label, which
 * matches the server render (auth starts as loading) and avoids a hydration
 * mismatch; it flips once `/auth/me` resolves.
 */
export function GetStartedButton({
  variant = "default",
}: {
  variant?: "default" | "outline";
}) {
  const { user, loading } = useAuth();
  const loggedIn = !loading && user !== null;

  return (
    <Link
      href={loggedIn ? "/upload" : "/login"}
      className={cn(buttonVariants({ variant }))}
    >
      {loggedIn ? "Go to the app" : "Get started"}
    </Link>
  );
}
