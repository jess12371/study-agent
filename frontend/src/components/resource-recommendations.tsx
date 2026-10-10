// Rekomendasi resource (F-06) — hasil semantic search pgvector untuk plan ini.
"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Sparkles } from "lucide-react";

import { ErrorState } from "@/components/error-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage, resourcesApi, type RecommendedResource } from "@/lib/api";

export function ResourceRecommendations({ planId }: { planId: string }) {
  const [resources, setResources] = useState<RecommendedResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResources(await resourcesApi.recommend(planId));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-32 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load resources"
        message={error}
        onRetry={load}
      />
    );
  }

  if (resources.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No recommendations yet. Try seeding the resource catalog.
      </p>
    );
  }

  // Sort by similarity desc, filter < 40%, fallback ke 5 teratas kalau terlalu sedikit.
  const sorted = [...resources].sort(
    (a, b) => (b.similarity_score ?? 0) - (a.similarity_score ?? 0)
  );
  const filtered = sorted.filter((r) => (r.similarity_score ?? 0) >= 0.4);
  const visible = filtered.length >= 5 ? filtered : sorted.slice(0, 5);

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {visible.map((resource) => {
        const score = resource.similarity_score
          ? Math.round(resource.similarity_score * 100)
          : null;
        const label =
          (resource.similarity_score ?? 0) >= 0.6
            ? { text: "Highly relevant", className: "border-transparent bg-emerald-600 text-white hover:bg-emerald-600" }
            : (resource.similarity_score ?? 0) >= 0.4
              ? { text: "Relevant", className: "border-transparent bg-amber-500 text-white hover:bg-amber-500" }
              : { text: "Related", className: "text-muted-foreground" };
        const body = (
          <Card className="h-full transition-shadow hover:shadow-md">
            <CardContent className="space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary" className="capitalize">
                  {resource.type ?? "resource"}
                </Badge>
                {resource.is_free ? (
                  <Badge className="border-transparent bg-emerald-600 text-white hover:bg-emerald-600">
                    Free
                  </Badge>
                ) : (
                  <Badge variant="outline">Paid</Badge>
                )}
                {resource.level && (
                  <Badge variant="outline" className="capitalize">
                    {resource.level}
                  </Badge>
                )}
                <Badge className={label.className}>{label.text}</Badge>
                {score !== null && (
                  <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                    <Sparkles className="h-3 w-3" />
                    {score}%
                  </span>
                )}
              </div>
              <p className="flex items-start gap-2 font-medium leading-snug">
                {resource.name}
                {resource.url && (
                  <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
              </p>
              {resource.description && (
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {resource.description}
                </p>
              )}
              {resource.skills.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {resource.skills.slice(0, 3).map((skill) => (
                    <span
                      key={skill}
                      className="rounded bg-muted px-1.5 py-0.5 text-[10px] capitalize text-muted-foreground"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        );

        return resource.url ? (
          <a
            key={resource.id}
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            {body}
          </a>
        ) : (
          <div key={resource.id}>{body}</div>
        );
      })}
    </div>
  );
}
