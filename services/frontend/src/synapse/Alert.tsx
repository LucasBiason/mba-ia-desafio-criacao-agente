import type { ComponentPropsWithoutRef } from "react";

type AlertProps = ComponentPropsWithoutRef<"div"> & {
  variant?: "info" | "success" | "warning" | "danger";
};

export function Alert({
  variant = "info",
  className = "",
  role = "note",
  ...props
}: AlertProps) {
  return (
    <div
      {...props}
      role={role}
      className={`syn-alert ${className}`.trim()}
      data-variant={variant}
    />
  );
}
