import Link from "next/link";
import type { CaseListItem } from "@/lib/types";

const categoryColors: Record<string, string> = {
  zoning: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  permits: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  water: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300",
  industry: "bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300",
};

const categoryLabels: Record<string, string> = {
  zoning: "Kaavoitus",
  permits: "Luvat",
  water: "Vesistöt",
  industry: "Teollisuus",
};

const confidenceColors: Record<string, string> = {
  high: "bg-green-500",
  medium: "bg-yellow-500",
  low: "bg-red-500",
};

const statusLabels: Record<string, string> = {
  proposed: "Ehdotettu",
  approved: "Hyväksytty",
  unknown: "Tuntematon",
};

const statusColors: Record<string, string> = {
  proposed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  approved:
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  unknown:
    "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300",
};

function getSummaryPreview(md: string): string {
  const lines = md.split("\n").filter((l) => l.trim());
  return lines.slice(0, 2).join(" ").slice(0, 160) + (md.length > 160 ? "..." : "");
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("fi-FI", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
  });
}

export default function CaseCard({ caseItem }: { caseItem: CaseListItem }) {
  const catColor =
    categoryColors[caseItem.primary_category] || categoryColors.industry;
  const catLabel =
    categoryLabels[caseItem.primary_category] || caseItem.primary_category;
  const confColor = confidenceColors[caseItem.confidence] || confidenceColors.low;
  const statLabel = statusLabels[caseItem.status] || caseItem.status;
  const statColor = statusColors[caseItem.status] || statusColors.unknown;

  return (
    <Link
      href={`/cases/${caseItem.slug}`}
      className="block rounded-xl border border-border bg-surface p-5 transition-all hover:shadow-md hover:border-primary/30 hover:bg-surface-hover"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${catColor}`}
          >
            {catLabel}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statColor}`}
          >
            {statLabel}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0" title={`Luottamus: ${caseItem.confidence}`}>
          <span className={`h-2.5 w-2.5 rounded-full ${confColor}`} />
          <span className="text-xs text-muted capitalize">{caseItem.confidence}</span>
        </div>
      </div>

      <h3 className="text-base font-semibold text-foreground mb-2 line-clamp-2">
        {caseItem.headline}
      </h3>

      <p className="text-sm text-muted mb-3 line-clamp-2">
        {getSummaryPreview(caseItem.summary_md)}
      </p>

      <div className="flex items-center justify-between text-xs text-muted">
        <div className="flex flex-wrap gap-1">
          {caseItem.municipalities_json?.map((m) => (
            <span
              key={m}
              className="rounded bg-primary-lighter px-1.5 py-0.5 text-primary font-medium"
            >
              {m}
            </span>
          ))}
        </div>
        <time dateTime={caseItem.first_seen_at}>
          {formatDate(caseItem.first_seen_at)}
        </time>
      </div>
    </Link>
  );
}
