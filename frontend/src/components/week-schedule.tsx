// Jadwal per minggu — tabs, sesi harian, progres, Focus Mode & Quiz.
"use client";

import { useState } from "react";
import { CalendarPlus, Clock, Loader2, Timer } from "lucide-react";

import { FocusMode } from "@/components/focus-mode";
import { QuizDialog } from "@/components/quiz-dialog";
import { SessionCheckbox } from "@/components/session-checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  progressSessionKey,
  type DaySession,
  type ProgressEntry,
  type ProgressStatus,
  type WeekSchedule,
} from "@/lib/api";

interface FocusTarget {
  weekNumber: number;
  session: DaySession;
  sessionIndex: number;
}

export function WeekScheduleView({
  weeks,
  progress,
  onMark,
  updating,
  planId,
  totalWeeks,
  onGenerateNextMonth,
  generatingNext,
}: {
  weeks: WeekSchedule[];
  progress?: Record<string, ProgressEntry>;
  onMark?: (
    weekNumber: number,
    session: DaySession,
    sessionIndex: number,
    status: ProgressStatus
  ) => void;
  updating?: boolean;
  planId?: string;
  totalWeeks?: number;
  onGenerateNextMonth?: () => void;
  generatingNext?: boolean;
}) {
  const [focus, setFocus] = useState<FocusTarget | null>(null);

  const lastWeek = weeks[weeks.length - 1];
  const lastWeekTouched =
    lastWeek?.days.some((session, index) => {
      const key = progressSessionKey(lastWeek.week, session.day, index);
      const status = progress?.[key]?.status;
      return status === "completed" || status === "skipped";
    }) ?? false;
  const canGenerateNext = weeks.length % 4 === 0 && lastWeekTouched;

  if (weeks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No weekly schedule available.
      </p>
    );
  }

  return (
    <>
      <Tabs defaultValue={`week-${weeks[0].week}`} className="w-full">
        <div className="overflow-x-auto pb-1">
          <TabsList className="h-auto flex-wrap">
            {weeks.map((week) => (
              <TabsTrigger key={week.week} value={`week-${week.week}`}>
                Week {week.week}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {weeks.map((week) => (
          <TabsContent
            key={week.week}
            value={`week-${week.week}`}
            className="space-y-4"
          >
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Theme: </span>
              {week.theme}
            </p>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {week.days.map((session, index) => {
                const key = progressSessionKey(week.week, session.day, index);
                const entry = progress?.[key];
                const status: ProgressStatus = entry?.status ?? "pending";
                return (
                  <Card key={`${week.week}-${session.day}-${index}`}>
                    <CardContent className="space-y-2 p-4">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold">{session.day}</span>
                        <div className="flex items-center gap-1">
                          <Badge variant="outline" className="gap-1">
                            <Clock className="h-3 w-3" />
                            {session.time}
                          </Badge>
                          {onMark && (
                            <SessionCheckbox
                              status={status}
                              disabled={updating}
                              onSelect={(next) =>
                                onMark(week.week, session, index, next)
                              }
                            />
                          )}
                        </div>
                      </div>
                      <p className="text-sm font-medium">{session.topic}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.duration_minutes} min
                      </p>
                      {session.activities.length > 0 && (
                        <ul className="space-y-1 text-xs text-muted-foreground">
                          {session.activities.map((activity, i) => (
                            <li key={i} className="flex gap-1.5">
                              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                              {activity}
                            </li>
                          ))}
                        </ul>
                      )}

                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setFocus({
                              weekNumber: week.week,
                              session,
                              sessionIndex: index,
                            })
                          }
                        >
                          <Timer className="h-4 w-4" />
                          Start Focus
                        </Button>
                        {planId && (
                          <QuizDialog
                            planId={planId}
                            weekNumber={week.week}
                            dayName={session.day}
                          />
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {typeof totalWeeks === "number" &&
        totalWeeks > 0 &&
        weeks.length < totalWeeks &&
        weeks.length % 4 === 0 && (
          <div className="mt-4 space-y-2 rounded-xl border border-dashed p-4 text-center">
            {canGenerateNext ? (
              <>
                <p className="text-sm text-muted-foreground">
                  You&apos;ve reached the end of the scheduled month. Generate the
                  next 4 weeks to keep going.
                </p>
                <Button
                  onClick={onGenerateNextMonth}
                  disabled={generatingNext}
                >
                  {generatingNext ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CalendarPlus className="h-4 w-4" />
                  )}
                  Generate Next Month Schedule
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Complete a session in Week {lastWeek?.week} to unlock next
                month&apos;s schedule.
              </p>
            )}
          </div>
        )}

      <FocusMode
        open={focus !== null}
        topic={focus?.session.topic ?? ""}
        durationMinutes={25}
        onClose={() => setFocus(null)}
        onComplete={() => {
          if (focus && onMark) {
            onMark(focus.weekNumber, focus.session, focus.sessionIndex, "completed");
          }
        }}
      />
    </>
  );
}
