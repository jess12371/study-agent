// Panel chat dengan Study Agent (F-11) — riwayat, streaming, action buttons.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ChatMessageBubble } from "@/components/chat-message";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  chatApi,
  getErrorMessage,
  type ChatAction,
  type ChatMessage,
} from "@/lib/api";
import { useLanguage } from "@/lib/language-context";

export function ChatPanel({
  goalId,
  onPlanUpdated,
}: {
  goalId: string;
  onPlanUpdated?: () => void;
}) {
  const { t } = useLanguage();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const history = await chatApi.history(goalId);
      setMessages(Array.isArray(history) ? history : []);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [goalId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);
    setStreamText("");
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      await chatApi.stream(goalId, text, {
        onDelta: (chunk) => setStreamText((prev) => prev + chunk),
        onMessage: (message) => {
          setStreamText("");
          setMessages((prev) => [...prev, message]);
        },
      });
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSending(false);
      setStreamText("");
    }
  };

  const handleAction = async (action: ChatAction) => {
    setActionBusy(true);
    try {
      const result = await chatApi.executeAction(goalId, action.type, action.payload);
      if (result.type === "view_resource") {
        const url = result.data.url as string | undefined;
        toast.success(result.message);
        if (url) window.open(url, "_blank", "noopener,noreferrer");
      } else {
        toast.success(result.message);
        onPlanUpdated?.();
      }
      await load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setActionBusy(false);
    }
  };

  const handleClear = async () => {
    try {
      await chatApi.clear(goalId);
      setMessages([]);
      toast.success(t("chatCleared"));
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={handleClear}
            disabled={messages.length === 0}
          >
            <Trash2 className="h-4 w-4" />
            {t("clear")}
          </Button>
        </div>

        <div className="max-h-[420px] space-y-4 overflow-y-auto pr-1">
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-2/3 rounded-2xl" />
              <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
            </div>
          ) : messages.length === 0 && !streamText ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {t("chatEmpty")}
            </p>
          ) : (
            messages.map((message) => (
              <ChatMessageBubble
                key={message.id}
                message={message}
                onAction={handleAction}
                actionDisabled={actionBusy}
              />
            ))
          )}

          {(sending || streamText) && (
            <ChatMessageBubble
              message={{
                id: "streaming",
                role: "assistant",
                content: streamText || "…",
                created_at: new Date().toISOString(),
              }}
            />
          )}
          {sending && !streamText && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t("typing")}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex gap-2">
          <Input
            value={input}
            placeholder={t("chatPlaceholder")}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={sending}
          />
          <Button onClick={handleSend} disabled={sending || !input.trim()}>
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {t("send")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
