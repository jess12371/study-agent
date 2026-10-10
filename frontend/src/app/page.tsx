// Landing page — hero, fitur, dan footer.
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

const FEATURES = [
  {
    icon: Sparkles,
    title: "Personalized Plans",
    description:
      "A weekly schedule built around your goal, deadline, and working hours.",
  },
  {
    icon: ShieldCheck,
    title: "Feasibility Check",
    description:
      "Know upfront whether your target is realistic — and get alternatives if it isn't.",
  },
  {
    icon: LineChart,
    title: "Progress Tracking",
    description:
      "Mark sessions as done, skipped, or rescheduled and watch your streak grow.",
  },
  {
    icon: BookOpen,
    title: "Resource Recommendations",
    description:
      "Curated, mostly free resources matched to each topic and skill level.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main>
        {/* Hero */}
        <section className="container flex flex-col items-center gap-6 py-20 text-center md:py-28">
        <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-sm text-muted-foreground">
          <GraduationCap className="h-4 w-4" />
          Learn smarter, not harder
        </div>
        <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
          AI-Powered Study Plans for Your Goals
        </h1>
        <p className="max-w-2xl text-balance text-lg text-muted-foreground">
          Tell Study Agent what you want to learn and when you&apos;re free.
          Get a realistic, week-by-week plan with milestones and resources.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button size="lg" asChild>
            <Link href="/signup">
              Get Started Free
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/login">Log in</Link>
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
                <CardTitle className="text-lg">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
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
            <span>Study Agent</span>
          </div>
          <p>© {new Date().getFullYear()} Study Agent. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
