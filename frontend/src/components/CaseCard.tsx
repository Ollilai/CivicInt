import Link from "next/link";
import type { CaseListItem } from "@/lib/types";

const categoryColors: Record<string, string> = {
  maankaytto: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  rakentaminen: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  luonnonvarat: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  vesistot: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300",
  vaikuttaminen: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
};

const categoryLabels: Record<string, string> = {
  maankaytto: "Maankäyttö",
  rakentaminen: "Rakentaminen",
  luonnonvarat: "Luonnonvarat",
  vesistot: "Vesistöt",
  vaikuttaminen: "Vaikuttaminen",
};

const statusConfig: Record<string, { label: string; color: string; border: string }> = {
  valitusaika: {
    label: "Valitusaika",
    color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    border: "border-red-200 dark:border-red-900/50",
  },
  nahtavilla: {
    label: "Nähtävillä",
    color: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
    border: "border-orange-200 dark:border-orange-900/50",
  },
  vireilla: {
    label: "Vireillä",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    border: "border-border",
  },
  lainvoimainen: {
    label: "Lainvoimainen",
    color: "bg-gray-100 text-gray-500 dark:bg-gray-800/50 dark:text-gray-400",
    border: "border-border",
  },
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("fi-FI", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
  });
}

function getDeadlineText(deadline: string): { text: string; urgent: boolean } {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const dl = new Date(deadline);
  dl.setHours(0, 0, 0, 0);
  const days = Math.ceil((dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (days < 0) return { text: "Määräaika umpeutunut", urgent: false };
  if (days === 0) return { text: "Tänään!", urgent: true };
  if (days === 1) return { text: "Huomenna", urgent: true };
  if (days <= 7) return { text: `${days} pv jäljellä`, urgent: true };
  if (days <= 30) return { text: `${days} pv jäljellä`, urgent: false };
  return { text: formatDate(deadline), urgent: false };
}

export default function CaseCard({ caseItem }: { caseItem: CaseListItem }) {
  const catColor =
    categoryColors[caseItem.primary_category] || "bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300";
  const catLabel =
    categoryLabels[caseItem.primary_category] || caseItem.primary_category;
  const status = statusConfig[caseItem.status] || statusConfig.vireilla;

  const deadline = caseItem.action_deadline
    ? getDeadlineText(caseItem.action_deadline)
    : null;

  return (
    <Link
      href={`/cases/${caseItem.slug}`}
      className={`block rounded-xl border bg-surface p-5 transition-all hover:shadow-md hover:border-primary/30 hover:bg-surface-hover ${status.border}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${catColor}`}
          >
            {catLabel}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${status.color}`}
          >
            {status.label}
          </span>
        </div>
        {deadline && (
          <span
            className={`text-xs font-medium shrink-0 ${
              deadline.urgent
                ? "text-red-600 dark:text-red-400"
                : "text-muted"
            }`}
          >
            {deadline.text}
          </span>
        )}
      </div>

      <h3 className="text-base font-semibold text-foreground mb-3 line-clamp-2">
        {caseItem.headline}
      </h3>

      <div className="flex items-center justify-between text-xs text-muted">
        <div className="flex flex-wrap gap-1">
          {caseItem.municipalities?.map((m) => (
            <span
              key={m}
              className="rounded bg-primary-lighter px-1.5 py-0.5 text-primary font-medium"
            >
              {m}
            </span>
          ))}
        </div>
        <time dateTime={caseItem.meeting_date || caseItem.first_seen_at}>
          {caseItem.meeting_date
            ? formatDate(caseItem.meeting_date)
            : formatDate(caseItem.first_seen_at)}
        </time>
      </div>
    </Link>
  );
}
