import * as React from "react";
import {
  Dialog as PrimitiveDialog,
  Select as PrimitiveSelect,
  Switch as PrimitiveSwitch,
  Slot,
} from "radix-ui";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { X } from "lucide-react";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
// shadcn/ui composition: local, editable components with Radix primitives.
const buttonVariants = cva("button", {
  variants: {
    variant: {
      default: "primary",
      secondary: "secondary",
      ghost: "ghost",
      destructive: "destructive",
    },
    size: { default: "", sm: "small" },
  },
  defaultVariants: { variant: "default", size: "default" },
});
export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot.Root : "button";
  return (
    <Component
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}
export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      className={cn("input", className)}
      spellCheck={false}
      autoCapitalize="none"
      autoCorrect="off"
      {...props}
    />
  );
}
type SelectOption = { value: string; label: string; disabled?: boolean };
export function Select({
  value,
  onValueChange,
  options,
  name,
  disabled,
  className,
  ...props
}: {
  value: string;
  onValueChange: (value: string) => void;
  options: readonly SelectOption[];
  name?: string;
  disabled?: boolean;
} & Pick<
  React.ComponentProps<"button">,
  "id" | "className" | "aria-label" | "aria-labelledby" | "aria-describedby"
>) {
  // Radix reserves "" for its placeholder. Prefix every value so a real empty
  // choice and strings resembling a sentinel both round-trip without collisions.
  const encode = (item: string) => `value:${item}`;
  return (
    <>
      {name && (
        <input type="hidden" name={name} value={value} disabled={disabled} />
      )}
      <PrimitiveSelect.Root
        value={encode(value)}
        onValueChange={(next) => onValueChange(next.slice("value:".length))}
        disabled={disabled}
      >
        <PrimitiveSelect.Trigger
          data-slot="select"
          className={cn("select-trigger", className)}
          {...props}
        >
          <PrimitiveSelect.Value>
            {options.find((item) => item.value === value)?.label}
          </PrimitiveSelect.Value>
          <PrimitiveSelect.Icon className="select-chevron" aria-hidden>
            ▾
          </PrimitiveSelect.Icon>
        </PrimitiveSelect.Trigger>
        <PrimitiveSelect.Portal>
          <PrimitiveSelect.Content
            className="select-content"
            position="popper"
            sideOffset={5}
            collisionPadding={10}
          >
            <PrimitiveSelect.Viewport className="select-viewport">
              {options.map((item) => (
                <PrimitiveSelect.Item
                  className="select-item"
                  key={item.value}
                  value={encode(item.value)}
                  disabled={item.disabled}
                >
                  <PrimitiveSelect.ItemIndicator
                    className="select-check"
                    aria-hidden
                  >
                    ✓
                  </PrimitiveSelect.ItemIndicator>
                  <PrimitiveSelect.ItemText>
                    {item.label}
                  </PrimitiveSelect.ItemText>
                </PrimitiveSelect.Item>
              ))}
            </PrimitiveSelect.Viewport>
          </PrimitiveSelect.Content>
        </PrimitiveSelect.Portal>
      </PrimitiveSelect.Root>
    </>
  );
}
export function Card({ className, ...props }: React.ComponentProps<"section">) {
  return (
    <section data-slot="card" className={cn("card", className)} {...props} />
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={cn("badge", tone)}>{children}</span>;
}
export function Switch({
  checked,
  onCheckedChange,
  label,
  disabled,
}: {
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  const id = React.useId();
  return (
    <label className="switch-label" htmlFor={id}>
      <PrimitiveSwitch.Root
        className="switch"
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
      >
        <PrimitiveSwitch.Thumb className="switch-thumb" />
      </PrimitiveSwitch.Root>
      {label}
    </label>
  );
}
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const opener = React.useRef<HTMLElement | null>(null);
  return (
    <PrimitiveDialog.Root open={open} onOpenChange={onOpenChange}>
      <PrimitiveDialog.Portal>
        <PrimitiveDialog.Overlay className="dialog-overlay" />
        <PrimitiveDialog.Content
          className="dialog"
          onOpenAutoFocus={() => {
            opener.current = document.activeElement as HTMLElement | null;
          }}
          onCloseAutoFocus={(event) => {
            if (opener.current?.isConnected) {
              event.preventDefault();
              opener.current.focus();
            }
          }}
        >
          <PrimitiveDialog.Title className="dialog-title">
            {title}
          </PrimitiveDialog.Title>
          <PrimitiveDialog.Description className="muted">
            {description}
          </PrimitiveDialog.Description>
          {children}
          <PrimitiveDialog.Close asChild>
            <Button variant="ghost" className="close" aria-label="Fermer">
              <X size={18} />
            </Button>
          </PrimitiveDialog.Close>
        </PrimitiveDialog.Content>
      </PrimitiveDialog.Portal>
    </PrimitiveDialog.Root>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
