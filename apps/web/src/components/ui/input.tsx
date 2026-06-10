import * as React from "react";
import { cn } from "@/lib/utils";

/** Shared field styling for inputs, selects, and file/date controls. */
export const fieldClass = cn(
  "h-10 rounded-lg border border-input bg-card px-3 text-sm text-foreground",
  "transition-colors placeholder:text-muted-foreground",
  "focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
  "disabled:cursor-not-allowed disabled:opacity-50",
);

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(fieldClass, className)} {...props} />
  ),
);
Input.displayName = "Input";

export { Input };
