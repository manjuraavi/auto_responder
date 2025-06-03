import React from "react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "danger" | "outline";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-indigo-600 text-white hover:bg-indigo-700",
  secondary:
    "bg-gray-100 text-gray-700 hover:bg-gray-200",
  danger:
    "bg-red-500 text-white hover:bg-red-600",
  outline:
    "border border-indigo-600 text-indigo-600 bg-white hover:bg-indigo-50",
};

const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  loading = false,
  className,
  children,
  ...props
}) => (
  <button
    className={clsx(
      "px-5 py-2 rounded-lg font-semibold shadow transition focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-60",
      variantClasses[variant],
      className
    )}
    disabled={loading || props.disabled}
    {...props}
  >
    {loading ? (
      <span className="flex items-center gap-2">
        <svg className="animate-spin h-5 w-5 text-current" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
        Loading...
      </span>
    ) : (
      children
    )}
  </button>
);

export default Button;