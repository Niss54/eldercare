import { HTMLAttributes } from "react";

type Props = HTMLAttributes<HTMLElement> & {
  as?: "article" | "section" | "div";
};

export function Card({ as = "article", className, ...props }: Props) {
  const Component = as;
  return <Component className={["card", className].filter(Boolean).join(" ")} {...props} />;
}
