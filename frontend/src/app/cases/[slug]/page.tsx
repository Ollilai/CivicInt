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
  maankaytto: "Maankäyttö",
  rakentaminen: "Rakentaminen",
  luonnonvarat: "Luonnonvarat",
  vesistot: "Vesistöt",
  vaikuttaminen: "Vaikuttaminen",
};

const categoryColors: Record<string, string> = {
  maankaytto: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  rakentaminen: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  luonnonvarat: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  vesistot: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300",
  vaikuttaminen: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
};

const statusConfig: Record<string, { label: string; description: string; color: string }> = {
  valitusaika: {
    label: "Valitusaika käynnissä",
    description: "Päätöksestä voi valittaa",
    color: "bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-900/50 dark:text-red-300",
  },
  nahtavilla: {
    label: "Nähtävillä",
    description: "Lausuntoja ja mielipiteitä voi jättää",
    color: "bg-orange-50 border-orange-200 text-orange-800 dark:bg-orange-900/20 dark:border-orange-900/50 dark:text-orange-300",
  },
  vireilla: {
    label: "Vireillä",
    description: "Asia on valmisteltavana, ei vielä päätetty",
    color: "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-900/50 dark:text-blue-300",
  },
  lainvoimainen: {
    label: "Lainvoimainen",
    description: "Päätös on lopullinen",
    color: "bg-gray-50 border-gray-200 text-gray-600 dark:bg-gray-800/30 dark:border-gray-700 dark:text-gray-400",
  },
};

const entityLabels: Record<string, string> = {
  applicant: "Hakija/toimija",
  permit_number: "Lupanumero",
  project_name: "Hankkeen nimi",
  location: "Sijainti",
  area_hectares: "Pinta-ala (ha)",
  developer: "Kehittäjä",
  contractor: "Urakoitsija",
  consultant: "Konsultti",
};

function renderMarkdown(md: string): string {
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

function getDeadlineInfo(deadline: string): { text: string; urgent: boolean } {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const dl = new Date(deadline);
  dl.setHours(0, 0, 0, 0);
  const days = Math.ceil((dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (days < 0) return { text: `Määräaika umpeutui ${formatDate(deadline)}`, urgent: false };
  if (days === 0) return { text: "Määräaika tänään!", urgent: true };
  if (days === 1) return { text: "Määräaika huomenna", urgent: true };
  if (days <= 7) return { text: `${days} päivää jäljellä (${formatDate(deadline)})`, urgent: true };
  return { text: `${days} päivää jäljellä (${formatDate(deadline)})`, urgent: false };
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
    categoryColors[caseData.primary_category] || "bg-slate-100 text-slate-800";
  const catLabel =
    categoryLabels[caseData.primary_category] || caseData.primary_category;
  const status = statusConfig[caseData.status] || statusConfig.vireilla;
  const deadline = caseData.action_deadline
    ? getDeadlineInfo(caseData.action_deadline)
    : null;

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

      {/* Action banner */}
      <div className={`rounded-lg border p-4 mb-6 ${status.color}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-sm">{status.label}</p>
            <p className="text-sm opacity-80">{status.description}</p>
          </div>
          {deadline && (
            <span
              className={`text-sm font-semibold shrink-0 ${
                deadline.urgent ? "" : "opacity-80"
              }`}
            >
              {deadline.text}
            </span>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${catColor}`}>
            {catLabel}
          </span>
          {caseData.municipalities && caseData.municipalities.length > 0 &&
            caseData.municipalities.map((m) => (
              <span
                key={m}
                className="rounded-full bg-primary-lighter px-2.5 py-0.5 text-primary text-xs font-medium"
              >
                {m}
              </span>
            ))}
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-2">
          {caseData.headline}
        </h1>

        <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
          {caseData.meeting_date && (
            <span>Kokouspäivä: {formatDate(caseData.meeting_date)}</span>
          )}
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

      {/* Entities */}
      {caseData.entities &&
        Object.keys(caseData.entities).length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-foreground mb-3">
              Osapuolet ja tiedot
            </h2>
            <div className="bg-surface rounded-lg border border-border p-5">
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(caseData.entities).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs font-medium text-muted uppercase tracking-wide">
                      {entityLabels[key] || key.replace(/_/g, " ")}
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
                    {event.event_time && (
                      <span className="text-sm font-medium text-foreground">
                        {formatDate(event.event_time)}
                      </span>
                    )}
                  </div>
                  {event.payload && (
                    <p className="text-sm text-muted">
                      {typeof event.payload === "object" && "description" in event.payload
                        ? String(event.payload.description)
                        : JSON.stringify(event.payload)}
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
            Lähteet
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
                  {ev.page && <span>Sivu {ev.page}</span>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
