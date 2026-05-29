"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import type { CaseDetail } from "@/lib/types";
import { getCaseBySlug } from "@/lib/api";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("fi-FI", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("fi-FI", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const categoryLabels: Record<string, string> = {
  zoning: "Kaavoitus",
  permits: "Luvat",
  water: "Vesistöt",
  industry: "Teollisuus",
};

const categoryColors: Record<string, string> = {
  zoning: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  permits: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  water: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300",
  industry: "bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300",
};

const statusLabels: Record<string, string> = {
  proposed: "Ehdotettu",
  approved: "Hyväksytty",
  unknown: "Tuntematon",
};

const confidenceLabels: Record<string, string> = {
  high: "Korkea",
  medium: "Keskitaso",
  low: "Matala",
};

const confidenceColors: Record<string, string> = {
  high: "text-green-600 dark:text-green-400",
  medium: "text-yellow-600 dark:text-yellow-400",
  low: "text-red-600 dark:text-red-400",
};

const eventTypeLabels: Record<string, string> = {
  decision: "Päätös",
  hearing: "Kuuleminen",
  application: "Hakemus",
  comment: "Lausunto",
  appeal: "Valitus",
  notification: "Ilmoitus",
};

function renderMarkdown(md: string): string {
  // Simple markdown rendering: bold, italic, headers, line breaks
  return md
    .replace(/^### (.*$)/gm, '<h3 class="text-base font-semibold mt-4 mb-1">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-lg font-semibold mt-4 mb-2">$1</h2>')
    .replace(/^# (.*$)/gm, '<h1 class="text-xl font-bold mt-4 mb-2">$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/^- (.*$)/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br />");
}

export default function CaseDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getCaseBySlug(slug)
      .then(setCaseData)
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Tapauksen haku epäonnistui"
        );
      })
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="skeleton h-6 w-32 mb-6" />
        <div className="skeleton h-8 w-3/4 mb-4" />
        <div className="flex gap-2 mb-6">
          <div className="skeleton h-6 w-20" />
          <div className="skeleton h-6 w-24" />
        </div>
        <div className="space-y-3">
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-2/3" />
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground mb-6"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Takaisin
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-900/20 p-4">
          <p className="text-sm text-red-700 dark:text-red-400">
            {error || "Tapausta ei löytynyt"}
          </p>
        </div>
      </div>
    );
  }

  const catColor =
    categoryColors[caseData.primary_category] || categoryColors.industry;
  const catLabel =
    categoryLabels[caseData.primary_category] || caseData.primary_category;

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8">
      {/* Back button */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground mb-6 transition-colors"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Takaisin
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${catColor}`}>
            {catLabel}
          </span>
          <span className="rounded-full bg-gray-100 dark:bg-gray-800 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
            {statusLabels[caseData.status] || caseData.status}
          </span>
          <span className={`text-xs font-medium ${confidenceColors[caseData.confidence] || ""}`}>
            Luottamus: {confidenceLabels[caseData.confidence] || caseData.confidence}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-2">
          {caseData.headline}
        </h1>

        <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
          {caseData.municipalities_json && caseData.municipalities_json.length > 0 && (
            <div className="flex gap-1">
              {caseData.municipalities_json.map((m) => (
                <span
                  key={m}
                  className="rounded bg-primary-lighter px-1.5 py-0.5 text-primary text-xs font-medium"
                >
                  {m}
                </span>
              ))}
            </div>
          )}
          <span>Havaittu: {formatDate(caseData.first_seen_at)}</span>
          {caseData.permit_number && (
            <span>Lupanumero: {caseData.permit_number}</span>
          )}
        </div>
      </div>

      {/* Summary */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-foreground mb-3">
          Yhteenveto
        </h2>
        <div
          className="prose prose-sm max-w-none text-foreground/90 leading-relaxed bg-surface rounded-lg border border-border p-5"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(caseData.summary_md) }}
        />
      </section>

      {/* Confidence reason */}
      {caseData.confidence_reason && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-3">
            Luottamuksen perustelu
          </h2>
          <p className="text-sm text-muted bg-surface rounded-lg border border-border p-4">
            {caseData.confidence_reason}
          </p>
        </section>
      )}

      {/* Entities */}
      {caseData.entities_json &&
        Object.keys(caseData.entities_json).length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-foreground mb-3">
              Osapuolet
            </h2>
            <div className="bg-surface rounded-lg border border-border p-5">
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(caseData.entities_json).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs font-medium text-muted uppercase tracking-wide">
                      {key}
                    </dt>
                    <dd className="text-sm text-foreground mt-0.5">
                      {Array.isArray(value) ? value.join(", ") : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>
        )}

      {/* Timeline */}
      {caseData.events.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-3">
            Aikajana
          </h2>
          <div className="space-y-3">
            {caseData.events.map((event) => (
              <div
                key={event.id}
                className="flex gap-3 bg-surface rounded-lg border border-border p-4"
              >
                <div className="mt-1 h-2 w-2 rounded-full bg-primary shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-foreground">
                      {eventTypeLabels[event.event_type] || event.event_type}
                    </span>
                    {event.event_time && (
                      <span className="text-xs text-muted">
                        {formatDateTime(event.event_time)}
                      </span>
                    )}
                  </div>
                  {event.payload_json && (
                    <p className="text-sm text-muted">
                      {JSON.stringify(event.payload_json)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Evidence */}
      {caseData.evidence.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-foreground mb-3">
            Lähteet ja todisteet
          </h2>
          <div className="space-y-3">
            {caseData.evidence.map((ev) => (
              <div
                key={ev.id}
                className="bg-surface rounded-lg border border-border p-4"
              >
                <blockquote className="text-sm text-foreground/80 border-l-2 border-primary pl-3 mb-2 italic">
                  {ev.snippet}
                </blockquote>
                <div className="flex items-center justify-between text-xs text-muted">
                  <a
                    href={ev.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline truncate max-w-[70%]"
                  >
                    {ev.source_url}
                  </a>
                  <div className="flex gap-3">
                    {ev.page && <span>Sivu {ev.page}</span>}
                    <span>{formatDateTime(ev.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Locations */}
      {caseData.locations_json &&
        Object.keys(caseData.locations_json).length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-foreground mb-3">
              Sijainnit
            </h2>
            <div className="bg-surface rounded-lg border border-border p-5">
              <pre className="text-sm text-foreground/80 whitespace-pre-wrap">
                {JSON.stringify(caseData.locations_json, null, 2)}
              </pre>
            </div>
          </section>
        )}
    </div>
  );
}
