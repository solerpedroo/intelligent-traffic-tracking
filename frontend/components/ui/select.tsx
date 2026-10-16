"use client";

import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;

export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        "flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-input bg-card px-3 text-sm text-foreground shadow-[inset_0_1px_0_oklch(1_0_0/0.08)]",
        "transition-[border-color,box-shadow] duration-[var(--duration-base)] ease-[var(--ease-premium)]",
        "hover:border-brand/25",
        "focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/20",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "data-[placeholder]:text-muted-foreground",
        "[&>span]:line-clamp-1",
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown
          className="size-4 shrink-0 text-muted-foreground"
          aria-hidden
        />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

export function SelectContent({
  className,
  children,
  position = "popper",
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        className={cn(
          "relative z-50 max-h-[min(24rem,70vh)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-[0_12px_32px_-8px_oklch(0_0_0/0.55)]",
          "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          position === "popper" && "data-[side=bottom]:translate-y-1",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.ScrollUpButton className="flex items-center justify-center py-1 text-muted-foreground">
          <ChevronUp className="size-4" />
        </SelectPrimitive.ScrollUpButton>
        <SelectPrimitive.Viewport className="w-full min-w-[var(--radix-select-trigger-width)] p-1">
          {children}
        </SelectPrimitive.Viewport>
        <SelectPrimitive.ScrollDownButton className="flex items-center justify-center py-1 text-muted-foreground">
          <ChevronDown className="size-4" />
        </SelectPrimitive.ScrollDownButton>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-md py-2 pr-2 pl-8 text-sm outline-none",
        "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground",
        "data-[state=checked]:font-medium",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4 text-brand" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

const PLACEHOLDER_VALUE = "__select_placeholder__";

function toItemValue(optionValue: string): string {
  if (
    optionValue === PLACEHOLDER_VALUE ||
    optionValue.startsWith(`${PLACEHOLDER_VALUE}:`)
  ) {
    return `${PLACEHOLDER_VALUE}:${optionValue}`;
  }
  return optionValue === "" ? `${PLACEHOLDER_VALUE}:` : optionValue;
}

function fromItemValue(itemValue: string): string {
  if (itemValue === PLACEHOLDER_VALUE) return "";
  const prefix = `${PLACEHOLDER_VALUE}:`;
  if (itemValue.startsWith(prefix)) return itemValue.slice(prefix.length);
  return itemValue;
}

export function LabeledSelect({
  label,
  value,
  onChange,
  options,
  placeholder = "Select",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  const selectedValue =
    value === "" && !options.some((option) => option.value === "")
      ? PLACEHOLDER_VALUE
      : toItemValue(value);
  return (
    <div className="grid gap-2">
      <span className="label-caps">{label}</span>
      <Select
        value={selectedValue}
        onValueChange={(next) => onChange(fromItemValue(next))}
      >
        <SelectTrigger aria-label={label}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={PLACEHOLDER_VALUE}>{placeholder}</SelectItem>
          {options.map((option) => {
            const itemValue = toItemValue(option.value);
            return (
              <SelectItem key={itemValue} value={itemValue}>
                {option.label}
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </div>
  );
}
