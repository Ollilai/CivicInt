"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { MunicipalityItem } from "@/lib/types";

const categories = [
  { value: "", label: "Kaikki" },
  { value: "zoning", label: "Kaavoitus" },
  { value: "permits", label: "Luvat" },
  { value: "water", label: "Vesistöt" },
  { value: "industry", label: "Teollisuus" },
];

const statuses = [
  { value: "", label: "Kaikki" },
  { value: "proposed", label: "Ehdotettu" },
  { value: "approved", label: "Hyväksytty" },
  { value: "unknown", label: "Tuntematon" },
];

interface FilterBarProps {
  municipalities: MunicipalityItem[];
}

export default function FilterBar({ municipalities }: FilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [searchValue, setSearchValue] = useState(
    searchParams.get("search") || ""
  );
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const currentCategory = searchParams.get("category") || "";
  const currentMunicipality = searchParams.get("municipality") || "";
  const currentStatus = searchParams.get("status") || "";

  const updateParams = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      // Reset to page 1 when filters change
      params.delete("page");
      router.push(`/?${params.toString()}`);
    },
    [router, searchParams]
  );

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      const currentSearch = searchParams.get("search") || "";
      if (searchValue !== currentSearch) {
        updateParams("search", searchValue);
      }
    }, 400);
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchValue, searchParams, updateParams]);

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          placeholder="Hae tapauksia..."
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Municipality dropdown */}
        <select
          value={currentMunicipality}
          onChange={(e) => updateParams("municipality", e.target.value)}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">Kaikki kunnat</option>
          {municipalities.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name} ({m.case_count})
            </option>
          ))}
        </select>

        {/* Category chips */}
        <div className="flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => updateParams("category", cat.value)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                currentCategory === cat.value
                  ? "bg-primary text-white"
                  : "bg-surface border border-border text-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <select
          value={currentStatus}
          onChange={(e) => updateParams("status", e.target.value)}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {statuses.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
