import { describe, expect, it } from "vitest";
import {
  getCategoryTotals,
  getMonthlyTrend,
  getSavingsRate,
  type Summary,
  type Transaction
} from "./domain";

const transactions: Transaction[] = [
  {
    id: 1,
    amount: 1000,
    occurred_at: new Date().toISOString(),
    description: "Products",
    category: { id: 1, name: "Food", type: "expense" }
  },
  {
    id: 2,
    amount: 500,
    occurred_at: new Date().toISOString(),
    description: "Taxi",
    category: { id: 2, name: "Transport", type: "expense" }
  },
  {
    id: 3,
    amount: 5000,
    occurred_at: new Date().toISOString(),
    description: "Salary",
    category: { id: 3, name: "Salary", type: "income" }
  }
];

describe("dashboard domain helpers", () => {
  it("groups totals by category", () => {
    const totals = getCategoryTotals(transactions);

    expect(totals[0]).toMatchObject({ name: "Salary", amount: 5000 });
    expect(totals.find((item) => item.name === "Food")?.share).toBeCloseTo(0.66, 1);
  });

  it("builds a six month trend", () => {
    expect(getMonthlyTrend(transactions)).toHaveLength(6);
  });

  it("calculates savings rate from summary", () => {
    const summary: Summary = { income: 100000, expense: 65000, balance: 35000 };

    expect(getSavingsRate(summary)).toBe(35);
  });
});
