// Landing page — hero, fitur, dan footer.
"use client";

import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  GraduationCap,
  LineChart,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLanguage } from "@/lib/language-context";

const FEATURES = [
  {
    icon: Sparkles,
    title: "featurePersonalizedTitle",
    description: "featurePersonalizedDesc",
  },
  {
    icon: ShieldCheck,
    title: "featureFeasibilityTitle",
    description: "featureFeasibilityDesc",
  },
  {
    icon: LineChart,
    title: "featureProgressTitle",
    description: "featureProgressDesc",
  },
  {
    icon: BookOpen,
    title: "featureResourcesTitle",
    description: "featureResourcesDesc",
  },
] as const;

export default function HomePage() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main>
        {/* Hero */}
        <section className="container flex flex-col items-center gap-6 py-20 text-center md:py-28">
        <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-sm text-muted-foreground">
          <GraduationCap className="h-4 w-4" />
          {t("heroBadge")}
        </div>
        <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
          {t("heroTitle")}
        </h1>
        <p className="max-w-2xl text-balance text-lg text-muted-foreground">
          {t("heroSubtitle")}
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button size="lg" asChild>
            <Link href="/signup">
              {t("getStartedFree")}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/login">{t("logIn")}</Link>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="container pb-24">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="h-full">
              <CardHeader>
                <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-lg">{t(feature.title)}</CardTitle>
                <CardDescription>{t(feature.description)}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container flex flex-col items-center justify-between gap-3 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-4 w-4" />
            <span>{t("appName")}</span>
          </div>
          <p>{t("footerRights", { year: new Date().getFullYear() })}</p>
        </div>
      </footer>
    </div>
  );
}
