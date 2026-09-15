export type CategoryType = "income" | "expense";

export type Category = {
  id: number;
  type: CategoryType;
  name: string;
  icon?: string | null;
  is_active?: boolean;
};

export type Transaction = {
  id: number;
  amount: number;
  description?: string | null;
  occurred_at: string;
  category: {
    id: number;
    name: string;
    icon?: string | null;
    type: CategoryType;
  };
};

export type Summary = {
  income: number;
  expense: number;
  balance: number;
};

export type CategoryTotal = {
  name: string;
  amount: number;
  type: CategoryType;
  share: number;
};

export type TrendPoint = {
  label: string;
  income: number;
  expense: number;
};

const monthFormatter = new Intl.DateTimeFormat("ru-RU", {
  month: "short"
});

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function getCategoryTotals(transactions: Transaction[]): CategoryTotal[] {
  const totals = new Map<string, CategoryTotal>();

  for (const transaction of transactions) {
    const key = `${transaction.category.type}:${transaction.category.name}`;
    const current = totals.get(key) ?? {
      name: transaction.category.name,
      amount: 0,
      type: transaction.category.type,
      share: 0
    };

    current.amount += transaction.amount;
    totals.set(key, current);
  }

  const totalExpense = [...totals.values()]
    .filter((item) => item.type === "expense")
    .reduce((sum, item) => sum + item.amount, 0);

  return [...totals.values()]
    .map((item) => ({
      ...item,
      share: item.type === "expense" && totalExpense > 0 ? item.amount / totalExpense : 0
    }))
    .sort((left, right) => right.amount - left.amount);
}

export function getMonthlyTrend(transactions: Transaction[]): TrendPoint[] {
  const now = new Date();
  const buckets = new Map<string, TrendPoint>();

  for (let index = 5; index >= 0; index -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - index, 1);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    buckets.set(key, {
      label: monthFormatter.format(date).replace(".", ""),
      income: 0,
      expense: 0
    });
  }

  for (const transaction of transactions) {
    const date = new Date(transaction.occurred_at);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    const bucket = buckets.get(key);

    if (!bucket) {
      continue;
    }

    bucket[transaction.category.type] += transaction.amount;
  }

  return [...buckets.values()];
}

export function getSavingsRate(summary: Summary): number {
  if (summary.income <= 0) {
    return 0;
  }

  return Math.round((summary.balance / summary.income) * 100);
}
