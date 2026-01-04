import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncateId(id: string, length: number = 8): string {
  if (id.length <= length) return id;
  return `${id.slice(0, length)}...`;
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    approved: "text-green-600",
    declined: "text-red-600",
    pending: "text-yellow-600",
    processing: "text-blue-600",
    under_review: "text-orange-600",
    cancelled: "text-gray-600",
  };
  return colors[status.toLowerCase()] || "text-gray-600";
}

export function getRiskGradeColor(grade: string): string {
  const colors: Record<string, string> = {
    AAA: "text-green-600",
    AA: "text-green-500",
    A: "text-green-400",
    BBB: "text-yellow-500",
    BB: "text-yellow-600",
    B: "text-orange-500",
    CCC: "text-orange-600",
    CC: "text-red-500",
    C: "text-red-600",
    D: "text-red-700",
  };
  return colors[grade] || "text-gray-600";
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
