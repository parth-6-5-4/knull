/* Adapted from Aceternity UI's bento-grid (ui.aceternity.com/components/bento-grid),
   kept as the grid shell only; console panels/stat cards act as the items via
   col/row span classes. */
import { cn } from "@/lib/utils";

export function BentoGrid({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={cn("grid grid-cols-2 gap-4 md:auto-rows-[7.5rem] md:grid-cols-4", className)}>
      {children}
    </div>
  );
}
