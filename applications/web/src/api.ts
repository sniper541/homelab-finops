import type { Category, Summary, Transaction } from "./domain";
import { mockCategories, mockSummary, mockTransactions } from "./mockData";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
const defaultUserId = Number(import.meta.env.VITE_USER_ID ?? "1");

type DashboardData = {
  summary: Summary;
  transactions: Transaction[];
  categories: Category[];
  isFallback: boolean;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardData(userId = defaultUserId): Promise<DashboardData> {
  try {
    const query = `user_id=${encodeURIComponent(userId)}`;
    const [summary, transactions, categories] = await Promise.all([
      getJson<Summary>(`/reports/summary?${query}`),
      getJson<Transaction[]>(`/transactions?${query}&limit=100`),
      getJson<Category[]>(`/categories?${query}`)
    ]);

    return {
      summary,
      transactions,
      categories,
      isFallback: false
    };
  } catch (error) {
    console.warn("Using dashboard fallback data", error);

    return {
      summary: mockSummary,
      transactions: mockTransactions,
      categories: mockCategories,
      isFallback: true
    };
  }
}
