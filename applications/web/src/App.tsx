import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Bot,
  CalendarDays,
  Check,
  Clock3,
  History,
  LayoutDashboard,
  LockKeyhole,
  LogIn,
  LogOut,
  PieChart,
  RefreshCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Wallet
} from "lucide-react";
import { getDashboardData } from "./api";
import { AuthenticationError, keycloak, logout } from "./auth";
import AuthScreen from "./AuthScreen";
import {
  formatCurrency,
  formatDate,
  getCategoryTotals,
  getMonthlyTrend,
  getSavingsRate,
  type Category,
  type Summary,
  type Transaction
} from "./domain";

type DashboardState = {
  summary: Summary;
  transactions: Transaction[];
  categories: Category[];
  isFallback: boolean;
};


const defaultState: DashboardState = {
  summary: { income: 0, expense: 0, balance: 0 },
  transactions: [],
  categories: [],
  isFallback: false
};

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

function StatCard({
  label,
  value,
  helper,
  tone,
  icon
}: {
  label: string;
  value: string;
  helper: string;
  tone: "income" | "expense" | "balance";
  icon: ReactNode;
}) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__icon">{icon}</div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{helper}</span>
      </div>
    </article>
  );
}

function TrendChart({ transactions }: { transactions: Transaction[] }) {
  const trend = getMonthlyTrend(transactions);
  const maxValue = Math.max(...trend.flatMap((item) => [item.income, item.expense]), 1);

  return (
    <section className="panel panel--wide" id="analytics">
      <div className="panel__header">
        <div>
          <span className="eyebrow">Analytics</span>
          <h2>Динамика за 6 месяцев</h2>
        </div>
        <BarChart3 aria-hidden="true" />
      </div>

      <div className="chart-legend" aria-label="Легенда графика">
        <span>Доходы</span><span>Расходы</span>
      </div>
      <div className="trend-chart">
        {trend.map((item) => (
          <div className="trend-chart__item" key={item.label}>
            <div className="trend-chart__bars">
              <span
                className="trend-chart__bar trend-chart__bar--income"
                style={{ height: `${Math.max((item.income / maxValue) * 100, 4)}%` }}
                title={`Доход: ${formatCurrency(item.income)}`}
              />
              <span
                className="trend-chart__bar trend-chart__bar--expense"
                style={{ height: `${Math.max((item.expense / maxValue) * 100, 4)}%` }}
                title={`Расход: ${formatCurrency(item.expense)}`}
              />
            </div>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function CategoryBreakdown({ transactions }: { transactions: Transaction[] }) {
  const totals = getCategoryTotals(transactions).filter((item) => item.type === "expense").slice(0, 5);
  const topShare = Math.round((totals[0]?.share ?? 0) * 100);

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <span className="eyebrow">Categories</span>
          <h2>Куда уходят деньги</h2>
        </div>
        <PieChart aria-hidden="true" />
      </div>

      <div className="category-orbit" style={{ "--share": `${topShare}%` } as React.CSSProperties}>
        <span>{topShare}%</span>
        <small>главная категория</small>
      </div>

      <div className="category-list">
        {totals.map((item) => (
          <div className="category-row" key={item.name}>
            <div className="category-row__meta">
              <span>{item.name}</span>
              <strong>{formatCurrency(item.amount)}</strong>
            </div>
            <div className="category-row__track">
              <span style={{ width: `${Math.round(item.share * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RecentTransactions({ transactions }: { transactions: Transaction[] }) {
  return (
    <section className="panel panel--wide" id="history">
      <div className="panel__header">
        <div>
          <span className="eyebrow">History</span>
          <h2>Последние операции</h2>
        </div>
        <History aria-hidden="true" />
      </div>

      <div className="transactions">
        {transactions.length === 0 && <p className="empty-state">Пока нет операций.</p>}
        {transactions.slice(0, 8).map((transaction) => {
          const isIncome = transaction.category.type === "income";

          return (
            <div className="transaction-row" key={transaction.id}>
              <div className={`transaction-row__icon ${isIncome ? "is-income" : "is-expense"}`}>
                {isIncome ? <ArrowUpRight aria-hidden="true" /> : <ArrowDownRight aria-hidden="true" />}
              </div>
              <div className="transaction-row__main">
                <strong>{transaction.description || transaction.category.name}</strong>
                <span>
                  {transaction.category.name} · {formatDate(transaction.occurred_at)}
                </span>
              </div>
              <strong className={isIncome ? "amount income" : "amount expense"}>
                {isIncome ? "+" : "-"}
                {formatCurrency(transaction.amount)}
              </strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Dashboard({
  dashboard,
  isLoading,
  onLogout,
  onRefresh
}: {
  dashboard: DashboardState;
  isLoading: boolean;
  onLogout: () => void;
  onRefresh: () => void;
}) {
  const savingsRate = getSavingsRate(dashboard.summary);
  const operationCount = dashboard.transactions.length;
  const activeCategories = useMemo(
    () => dashboard.categories.filter((category) => category.is_active !== false).length,
    [dashboard.categories]
  );

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">
          <div className="brand__mark">
            <Wallet aria-hidden="true" />
          </div>
          <div>
            <strong>FinOps</strong>
            <span>Private analytics</span>
          </div>
        </div>

        <nav className="nav-list">
          <a href="#dashboard" className="is-active">
            <LayoutDashboard aria-hidden="true" />
            Обзор
          </a>
          <a href="#analytics">
            <BarChart3 aria-hidden="true" />
            Аналитика
          </a>
          <a href="#history">
            <Clock3 aria-hidden="true" />
            История
          </a>
          <a href="#reports">
            <ShieldCheck aria-hidden="true" />
            Отчеты
          </a>
        </nav>

        <div className="bot-card">
          <Bot aria-hidden="true" />
          <strong>Telegram остается быстрым вводом</strong>
          <span>Web отвечает за обзор, отчеты и контроль бюджета.</span>
        </div>
      </aside>

      <section className="content" id="dashboard">
        <header className="topbar">
          <div>
            <span className="eyebrow">FinOps web · premium MVP</span>
            <h1>Финансовый cockpit</h1>
          </div>

          <div className="topbar__actions">
            <div className="search-box">
              <Search aria-hidden="true" />
              <span>История, категории, отчеты</span>
            </div>
            <button className="primary-button" type="button" onClick={onRefresh} disabled={isLoading} aria-busy={isLoading}>
              <RefreshCcw aria-hidden="true" className={isLoading ? "is-spinning" : ""} />
              Обновить
            </button>
            <button className="ghost-button" type="button" onClick={onLogout}>
              <LogOut aria-hidden="true" />
              Выйти
            </button>
          </div>
        </header>

        <section className="hero-band">
          <div className="hero-band__copy">
            <Pill>
              <Sparkles aria-hidden="true" />
              {dashboard.isFallback ? "Demo data" : "FastAPI online"}
            </Pill>
            <h2>Один экран, чтобы понять месяц без лишнего шума.</h2>
            <p>
              Ввод остается в Telegram, а здесь собраны баланс, динамика, категории, последние операции и статус
              отчетов.
            </p>
          </div>
          <div className="hero-meter" aria-label="Процент накоплений">
            <span>{savingsRate}%</span>
            <small>остается после расходов</small>
          </div>
        </section>

        <section className="stats-grid" aria-label="Финансовая сводка">
          <StatCard
            label="Доходы"
            value={formatCurrency(dashboard.summary.income)}
            helper="За выбранный период"
            tone="income"
            icon={<ArrowUpRight aria-hidden="true" />}
          />
          <StatCard
            label="Расходы"
            value={formatCurrency(dashboard.summary.expense)}
            helper="Контроль бюджета"
            tone="expense"
            icon={<ArrowDownRight aria-hidden="true" />}
          />
          <StatCard
            label="Баланс"
            value={formatCurrency(dashboard.summary.balance)}
            helper={`${savingsRate}% остается после расходов`}
            tone="balance"
            icon={<Wallet aria-hidden="true" />}
          />
        </section>

        <section className="dashboard-grid">
          <TrendChart transactions={dashboard.transactions} />
          <CategoryBreakdown transactions={dashboard.transactions} />
          <RecentTransactions transactions={dashboard.transactions} />

          <section className="panel" id="reports">
            <div className="panel__header">
              <div>
                <span className="eyebrow">Reports</span>
                <h2>MVP-отчеты</h2>
              </div>
              <ShieldCheck aria-hidden="true" />
            </div>

            <div className="report-list">
              <div>
                <span>Операций в выборке</span>
                <strong>{operationCount}</strong>
              </div>
              <div>
                <span>Активных категорий</span>
                <strong>{activeCategories}</strong>
              </div>
              <div>
                <span>Источник данных</span>
                <strong>{dashboard.isFallback ? "Fallback" : "FastAPI"}</strong>
              </div>
              <div>
                <span>Текущий период</span>
                <strong>
                  <CalendarDays aria-hidden="true" />
                  Месяц
                </strong>
              </div>
              <div className="report-list__ready">
                <span>Защита аккаунта</span>
                <strong>
                  <Check aria-hidden="true" />
                  Keycloak
                </strong>
              </div>
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardState>(defaultState);
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(keycloak.authenticated));
  const [message, setMessage] = useState("");

  async function refreshDashboard() {
    setIsLoading(true);
    setMessage("");
    try {
      const nextDashboard = await getDashboardData();
      if (keycloak.authenticated) setDashboard(nextDashboard);
    } catch (error) {
      setDashboard(defaultState);
      setMessage(error instanceof Error ? error.message : "Не удалось загрузить данные.");
      if (error instanceof AuthenticationError) setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogout() {
    try { await logout(); }
    catch { setMessage("Не удалось завершить сессию. Попробуйте выйти ещё раз."); }
  }

  useEffect(() => {
    keycloak.onAuthLogout = () => {
      setIsAuthenticated(false);
      setDashboard(defaultState);
      setMessage("Сессия завершена. Войдите снова.");
    };
    if (isAuthenticated) void refreshDashboard();
    return () => { keycloak.onAuthLogout = undefined; };
  }, [isAuthenticated]);

  if (!isAuthenticated) return <AuthScreen message={message} />;

  return (
    <>
      {message && <p className="dashboard-message" role="alert">{message}</p>}
      <Dashboard
        dashboard={dashboard}
        isLoading={isLoading}
        onLogout={handleLogout}
        onRefresh={refreshDashboard}
      />
    </>
  );
}
