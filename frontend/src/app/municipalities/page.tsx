"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { MunicipalityItem } from "@/lib/types";
import { getMunicipalities } from "@/lib/api";

export default function MunicipalitiesPage() {
  const [municipalities, setMunicipalities] = useState<MunicipalityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMunicipalities()
      .then((data) => {
        setMunicipalities(data.sort((a, b) => b.case_count - a.case_count));
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Kuntien haku epäonnistui"
        );
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground mb-1">Kunnat</h1>
        <p className="text-sm text-muted">
          Seurannassa olevat Lapin kunnat ja niiden tapausmäärät
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-900/20 p-4 mb-6">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-border bg-surface p-5"
            >
              <div className="skeleton h-6 w-3/4 mb-2" />
              <div className="skeleton h-4 w-1/2" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {municipalities.map((m) => (
            <Link
              key={m.name}
              href={`/?municipality=${encodeURIComponent(m.name)}`}
              className="rounded-xl border border-border bg-surface p-5 transition-all hover:shadow-md hover:border-primary/30 hover:bg-surface-hover group"
            >
              <h2 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
                {m.name}
              </h2>
              <p className="text-sm text-muted mt-1">
                {m.case_count}{" "}
                {m.case_count === 1 ? "tapaus" : "tapausta"}
              </p>
            </Link>
          ))}
        </div>
      )}

      {!loading && municipalities.length === 0 && !error && (
        <div className="text-center py-16">
          <p className="text-muted text-sm">Kuntia ei löytynyt.</p>
        </div>
      )}
    </div>
  );
}
