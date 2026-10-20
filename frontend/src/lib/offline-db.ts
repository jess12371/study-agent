// IndexedDB (via `idb`) untuk data offline: goal, study plan, progress, dan queue.
"use client";

import { openDB, type IDBPDatabase } from "idb";

import type { Goal, PlanResponse, ProgressEntry, ProgressMark } from "@/lib/api";

const DB_NAME = "study-agent-offline";
const DB_VERSION = 2;

export interface QueuedProgress {
  id: string;
  planId: string;
  payload: ProgressMark;
  createdAt: number;
}

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains("goals")) {
          db.createObjectStore("goals", { keyPath: "goalId" });
        }
        if (!db.objectStoreNames.contains("plans")) {
          db.createObjectStore("plans", { keyPath: "goalId" });
        }
        if (!db.objectStoreNames.contains("progress")) {
          db.createObjectStore("progress", { keyPath: "planId" });
        }
        if (!db.objectStoreNames.contains("queue")) {
          db.createObjectStore("queue", { keyPath: "id" });
        }
      },
    });
  }
  return dbPromise;
}

export async function cacheGoal(goalId: string, goal: Goal): Promise<void> {
  const db = await getDB();
  await db.put("goals", { goalId, goal, updatedAt: Date.now() });
}

export async function getCachedGoal(goalId: string): Promise<Goal | null> {
  const db = await getDB();
  const row = await db.get("goals", goalId);
  return row?.goal ?? null;
}

export async function cachePlan(goalId: string, plan: PlanResponse): Promise<void> {
  const db = await getDB();
  await db.put("plans", { goalId, plan, updatedAt: Date.now() });
}

export async function getCachedPlan(goalId: string): Promise<PlanResponse | null> {
  const db = await getDB();
  const row = await db.get("plans", goalId);
  return row?.plan ?? null;
}

export async function cacheProgress(
  planId: string,
  entries: ProgressEntry[]
): Promise<void> {
  const db = await getDB();
  await db.put("progress", { planId, entries, updatedAt: Date.now() });
}

export async function getCachedProgress(
  planId: string
): Promise<ProgressEntry[] | null> {
  const db = await getDB();
  const row = await db.get("progress", planId);
  return row?.entries ?? null;
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function enqueueProgress(
  planId: string,
  payload: ProgressMark
): Promise<string> {
  const db = await getDB();
  const id = newId();
  await db.put("queue", {
    id,
    planId,
    payload,
    createdAt: Date.now(),
  } satisfies QueuedProgress);
  return id;
}

export async function getQueue(): Promise<QueuedProgress[]> {
  const db = await getDB();
  const items = (await db.getAll("queue")) as QueuedProgress[];
  return items.sort((a, b) => a.createdAt - b.createdAt);
}

export async function removeQueued(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("queue", id);
}

export async function clearQueue(): Promise<void> {
  const db = await getDB();
  await db.clear("queue");
}
