import type { Category, Summary, Transaction } from "./domain";
import { mockCategories, mockSummary, mockTransactions } from "./mockData";
import { AuthenticationError, getAccessToken } from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
const defaultUserId = Number(import.meta.env.VITE_USER_ID ?? "1");

type DashboardData = {
  summary: Summary;
  transactions: Transaction[];
  categories: Category[];
  isFallback: boolean;
};

async function getJson<T>(path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`
    }
  });

  if (response.status === 401 || response.status === 403) {
    throw new AuthenticationError("Нет доступа к API. Попробуйте войти снова.");
  }
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardData(userId = defaultUserId): Promise<DashboardData> {
  const token = await getAccessToken();
  try {
    // Temporary compatibility until FastAPI derives the user from a verified JWT.
    const query = `user_id=${encodeURIComponent(userId)}`;
    const [summary, transactions, categories] = await Promise.all([
      getJson<Summary>(`/reports/summary?${query}`, token),
      getJson<Transaction[]>(`/transactions?${query}&limit=100`, token),
      getJson<Category[]>(`/categories?${query}`, token)
    ]);

    return {
      summary,
      transactions,
      categories,
      isFallback: false
    };
  } catch (error) {
    if (error instanceof AuthenticationError) throw error;
    console.warn("Using dashboard fallback data", error);

    return {
      summary: mockSummary,
      transactions: mockTransactions,
      categories: mockCategories,
      isFallback: true
    };
  }
}
