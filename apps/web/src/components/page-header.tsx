import type { LucideIcon } from "lucide-react";

/** Consistent page title block for the in-app (authenticated) pages. */
export function PageHeader({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="border-b pb-6">
      <div className="flex items-center gap-3">
        {Icon && (
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-5 w-5" aria-hidden />
          </span>
        )}
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
      </div>
      <p className="mt-3 max-w-2xl text-muted-foreground">{description}</p>
    </div>
  );
}
