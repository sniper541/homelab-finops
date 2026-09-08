import type { Category, Summary, Transaction } from "./domain";

const now = new Date();

function date(monthOffset: number, day: number, hour = 12): string {
  return new Date(now.getFullYear(), now.getMonth() + monthOffset, day, hour).toISOString();
}

export const mockSummary: Summary = {
  income: 245000,
  expense: 132400,
  balance: 112600
};

export const mockCategories: Category[] = [
  { id: 1, user_id: 1, type: "expense", name: "Products", icon: "cart" },
  { id: 2, user_id: 1, type: "expense", name: "Transport", icon: "car" },
  { id: 3, user_id: 1, type: "expense", name: "Home", icon: "home" },
  { id: 4, user_id: 1, type: "expense", name: "Subscriptions", icon: "card" },
  { id: 5, user_id: 1, type: "income", name: "Salary", icon: "briefcase" },
  { id: 6, user_id: 1, type: "income", name: "Freelance", icon: "laptop" }
];

export const mockTransactions: Transaction[] = [
  {
    id: 101,
    amount: 145000,
    description: "Salary",
    occurred_at: date(0, 2, 9),
    category: { id: 5, name: "Salary", icon: "briefcase", type: "income" }
  },
  {
    id: 102,
    amount: 100000,
    description: "Freelance project",
    occurred_at: date(0, 7, 18),
    category: { id: 6, name: "Freelance", icon: "laptop", type: "income" }
  },
  {
    id: 103,
    amount: 18400,
    description: "Weekly groceries",
    occurred_at: date(0, 10, 20),
    category: { id: 1, name: "Products", icon: "cart", type: "expense" }
  },
  {
    id: 104,
    amount: 4200,
    description: "Taxi and metro",
    occurred_at: date(0, 11, 8),
    category: { id: 2, name: "Transport", icon: "car", type: "expense" }
  },
  {
    id: 105,
    amount: 56000,
    description: "Rent and utilities",
    occurred_at: date(0, 5, 10),
    category: { id: 3, name: "Home", icon: "home", type: "expense" }
  },
  {
    id: 106,
    amount: 7800,
    description: "Cloud and apps",
    occurred_at: date(0, 13, 16),
    category: { id: 4, name: "Subscriptions", icon: "card", type: "expense" }
  },
  {
    id: 107,
    amount: 46000,
    description: "Products and cafes",
    occurred_at: date(-1, 16, 19),
    category: { id: 1, name: "Products", icon: "cart", type: "expense" }
  },
  {
    id: 108,
    amount: 205000,
    description: "August income",
    occurred_at: date(-1, 2, 9),
    category: { id: 5, name: "Salary", icon: "briefcase", type: "income" }
  },
  {
    id: 109,
    amount: 117000,
    description: "July expenses",
    occurred_at: date(-2, 12, 13),
    category: { id: 3, name: "Home", icon: "home", type: "expense" }
  },
  {
    id: 110,
    amount: 220000,
    description: "July income",
    occurred_at: date(-2, 2, 9),
    category: { id: 5, name: "Salary", icon: "briefcase", type: "income" }
  }
];
