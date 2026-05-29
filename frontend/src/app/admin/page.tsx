"use client";

import { useEffect, useState } from "react";
import type { PipelineStats, LLMSpend, Source } from "@/lib/types";
import {
  getPipelineStats,
  getLLMSpend,
  getSources,
} from "@/lib/api";

function formatEur(n: number): string {
  return n.toLocaleString("fi-FI", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("fi-FI", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminPage() {
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [spend, setSpend] = useState<LLMSpend | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getPipelineStats(), getLLMSpend(), getSources()])
      .then(([statsData, spendData, sourcesData]) => {
        setStats(statsData);
        setSpend(spendData);
        setSources(sourcesData);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Tietojen haku epäonnistui"
        );
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="skeleton h-8 w-48 mb-8" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 w-full rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-40 w-full rounded-xl mb-8" />
        <div className="skeleton h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-2xl font-bold text-foreground mb-6">Hallinta</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-900/20 p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  const spendPercentage =
    spend && spend.budget_eur > 0
      ? Math.min((spend.total_cost_eur / spend.budget_eur) * 100, 100)
      : 0;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-1">Hallinta</h1>
        <p className="text-sm text-muted">
          Putkilinjan tila ja kustannukset
        </p>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-xs font-medium text-muted uppercase tracking-wide">
              Lähteet
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats.enabled_sources}{" "}
              <span className="text-sm font-normal text-muted">
                / {stats.total_sources}
              </span>
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-xs font-medium text-muted uppercase tracking-wide">
              Dokumentit
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats.total_documents}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-xs font-medium text-muted uppercase tracking-wide">
              Tapaukset
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats.total_cases}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-xs font-medium text-muted uppercase tracking-wide">
              Tiedostot
            </p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats.total_files}
            </p>
          </div>
        </div>
      )}

      {/* Documents by status */}
      {stats && Object.keys(stats.documents_by_status).length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-5 mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4">
            Dokumentit statuksen mukaan
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {Object.entries(stats.documents_by_status).map(
              ([status, count]) => (
                <div
                  key={status}
                  className="flex items-center justify-between rounded-lg bg-background px-4 py-2.5"
                >
                  <span className="text-sm text-foreground capitalize">
                    {status}
                  </span>
                  <span className="text-sm font-semibold text-primary">
                    {count}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* LLM Spend */}
      {spend && (
        <div className="rounded-xl border border-border bg-surface p-5 mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-4">
            LLM-kustannukset ({spend.month})
          </h2>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm text-muted">
                {formatEur(spend.total_cost_eur)} / {formatEur(spend.budget_eur)}
              </span>
              <span className="text-sm font-medium text-foreground">
                {spendPercentage.toFixed(1)}%
              </span>
            </div>
            <div className="h-3 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  spendPercentage > 80
                    ? "bg-red-500"
                    : spendPercentage > 50
                      ? "bg-yellow-500"
                      : "bg-primary"
                }`}
                style={{ width: `${spendPercentage}%` }}
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <div>
              <p className="text-xs text-muted">Triage</p>
              <p className="text-sm font-medium text-foreground">
                {formatEur(spend.triage_cost)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Tapaustenrakentaja</p>
              <p className="text-sm font-medium text-foreground">
                {formatEur(spend.case_builder_cost)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Triagessa</p>
              <p className="text-sm font-medium text-foreground">
                {spend.documents_triaged} dok.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Rakennettu</p>
              <p className="text-sm font-medium text-foreground">
                {spend.cases_built} tapausta
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sources table */}
      {sources.length > 0 && (
        <div className="rounded-xl border border-border bg-surface overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-lg font-semibold text-foreground">Lähteet</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-background">
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Nimi
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Alusta
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Kunta
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Tila
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Viimeksi löydetty
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted">
                    Virhe
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sources.map((source) => (
                  <tr key={source.id} className="hover:bg-surface-hover">
                    <td className="px-4 py-3 font-medium text-foreground">
                      {source.name}
                    </td>
                    <td className="px-4 py-3 text-muted">{source.platform}</td>
                    <td className="px-4 py-3 text-muted">
                      {source.municipality}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                          source.enabled
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            source.enabled ? "bg-green-500" : "bg-red-500"
                          }`}
                        />
                        {source.enabled ? "Käytössä" : "Pois käytöstä"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {formatDate(source.last_discovered_at)}
                    </td>
                    <td className="px-4 py-3 text-xs text-red-600 dark:text-red-400 max-w-[200px] truncate">
                      {source.last_error || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
