"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import CaseCard from "@/components/CaseCard";
import FilterBar from "@/components/FilterBar";
import type { CaseListItem, MunicipalityItem, PaginatedResponse } from "@/lib/types";
import { getCases, getMunicipalities } from "@/lib/api";

function CasesFeed() {
  const searchParams = useSearchParams();
  const [cases, setCases] = useState<PaginatedResponse<CaseListItem> | null>(null);
  const [municipalities, setMunicipalities] = useState<MunicipalityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const page = Number(searchParams.get("page")) || 1;
  const municipality = searchParams.get("municipality") || undefined;
  const category = searchParams.get("category") || undefined;
  const status = searchParams.get("status") || undefined;
  const search = searchParams.get("search") || undefined;

  useEffect(() => {
    getMunicipalities()
      .then(setMunicipalities)
      .catch(() => {
        // Municipalities list is non-critical
      });
  }, []);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCases({
        page,
        per_page: 20,
        municipality,
        category,
        status,
        search,
      });
      setCases(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Tapausten haku epäonnistui"
      );
    } finally {
      setLoading(false);
    }
  }, [page, municipality, category, status, search]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-1">
          Ympäristötapaukset
        </h1>
        <p className="text-sm text-muted">
          Lapin kuntien ympäristöpäätösten seuranta
        </p>
      </div>

      <div className="mb-6">
        <FilterBar municipalities={municipalities} />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-900/20 p-4 mb-6">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface p-5">
              <div className="flex gap-2 mb-3">
                <div className="skeleton h-5 w-16" />
                <div className="skeleton h-5 w-20" />
              </div>
              <div className="skeleton h-5 w-full mb-2" />
              <div className="skeleton h-5 w-3/4 mb-3" />
              <div className="skeleton h-4 w-full mb-1" />
              <div className="skeleton h-4 w-2/3 mb-3" />
              <div className="flex justify-between">
                <div className="skeleton h-4 w-20" />
                <div className="skeleton h-4 w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : cases && cases.items.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cases.items.map((c) => (
              <CaseCard key={c.id} caseItem={c} />
            ))}
          </div>

          {/* Pagination */}
          {cases.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              {Array.from({ length: cases.pages }, (_, i) => i + 1).map(
                (p) => (
                  <a
                    key={p}
                    href={`?${new URLSearchParams({
                      ...(municipality ? { municipality } : {}),
                      ...(category ? { category } : {}),
                      ...(status ? { status } : {}),
                      ...(search ? { search } : {}),
                      page: String(p),
                    }).toString()}`}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      p === page
                        ? "bg-primary text-white"
                        : "bg-surface border border-border text-muted hover:bg-surface-hover"
                    }`}
                  >
                    {p}
                  </a>
                )
              )}
            </div>
          )}
        </>
      ) : (
        !loading && (
          <div className="text-center py-16">
            <svg
              className="mx-auto h-12 w-12 text-muted mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-muted text-sm">
              Ei tapauksia haullasi. Kokeile eri hakuehtoja.
            </p>
          </div>
        )
      )}
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <div className="skeleton h-8 w-48 mb-6" />
          <div className="skeleton h-12 w-full mb-4" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton h-48 w-full" />
            ))}
          </div>
        </div>
      }
    >
      <CasesFeed />
    </Suspense>
  );
}
