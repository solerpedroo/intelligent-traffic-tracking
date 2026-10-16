import { cva, type VariantProps } from "class-variance-authority";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-[background,border-color,box-shadow,transform] duration-[var(--duration-base)] ease-[var(--ease-premium)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border border-brand/40 bg-brand text-brand-foreground shadow-sm hover:bg-brand/90",
        secondary:
          "border border-border bg-secondary text-secondary-foreground hover:border-brand/30 hover:bg-accent",
        ghost:
          "border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
        destructive:
          "border border-destructive/40 bg-destructive/15 text-destructive-foreground hover:bg-destructive/25",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-11 rounded-lg px-6",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export function ButtonLink({
  href,
  children,
  variant = "default",
  size = "default",
  className,
}: {
  href: string;
  children: ReactNode;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  size?: VariantProps<typeof buttonVariants>["size"];
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(buttonVariants({ variant, size, className }))}
    >
      {children}
    </Link>
  );
}

export function buttonClassName(
  variant?: VariantProps<typeof buttonVariants>["variant"],
  size?: VariantProps<typeof buttonVariants>["size"],
) {
  return buttonVariants({ variant, size });
}
