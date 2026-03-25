import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({ variant = "primary", className, ...props }: Props) {
  const variantClass = variant === "ghost" ? "button ghost" : "button";
  return <button className={[variantClass, className].filter(Boolean).join(" ")} {...props} />;
}
