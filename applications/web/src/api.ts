import type { Category, Summary, Transaction } from "./domain";
import { AuthenticationError, getAccessToken } from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";

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

export async function getDashboardData(): Promise<DashboardData> {
  const token = await getAccessToken();
  try {
    const [summary, transactions, categories] = await Promise.all([
      getJson<Summary>("/reports/summary", token),
      getJson<Transaction[]>("/transactions?limit=100", token),
      getJson<Category[]>("/categories", token)
    ]);

    return {
      summary,
      transactions,
      categories,
      isFallback: false
    };
  } catch (error) {
    if (error instanceof AuthenticationError) throw error;
    throw new Error("Не удалось загрузить данные. Попробуйте обновить страницу позже.");
  }
}
