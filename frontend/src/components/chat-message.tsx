// Bubble satu pesan chat (user vs assistant) + action buttons (F-11).
"use client";

import { Bot } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ChatAction, ChatMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ChatMessageBubble({
  message,
  onAction,
  actionDisabled,
}: {
  message: ChatMessage;
  onAction?: (action: ChatAction) => void;
  actionDisabled?: boolean;
}) {
  const isUser = message.role === "user";
  const actions = message.actions ?? [];
  const time = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={cn("flex gap-2", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Bot className="h-4 w-4 text-primary" />
        </span>
      )}
      <div className={cn("max-w-[80%] space-y-2", isUser && "items-end")}>
        <div
          className={cn(
            "whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm",
            isUser
              ? "rounded-br-sm bg-primary text-primary-foreground"
              : "rounded-bl-sm bg-muted"
          )}
        >
          {message.content}
        </div>

        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map((action, index) => (
              <Button
                key={`${action.type}-${index}`}
                size="sm"
                variant="outline"
                disabled={actionDisabled}
                onClick={() => onAction?.(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}

        <p
          className={cn(
            "text-[10px] text-muted-foreground",
            isUser && "text-right"
          )}
        >
          {time}
        </p>
      </div>
    </div>
  );
}
