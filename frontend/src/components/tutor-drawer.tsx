// Floating Socratic Tutor (drawer/modal) — tanya jawab materi dengan streaming.
"use client";

import { useEffect, useRef, useState } from "react";
import { GraduationCap, Loader2, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage, tutorApi, type TutorMessage } from "@/lib/api";
import { useLanguage } from "@/lib/language-context";
import { cn } from "@/lib/utils";

export function TutorDrawer() {
  const { language, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState("General");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [streaming, setStreaming] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || sending) return;
    setInput("");
    const history = messages.slice(-10);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setSending(true);
    setStreaming("");

    let acc = "";
    try {
      await tutorApi.stream(
        { topic: topic.trim() || "General", question, history, language },
        {
          onDelta: (chunk) => {
            acc += chunk;
            setStreaming(acc);
          },
        }
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: acc || t("noResponse") },
      ]);
      setStreaming("");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSending(false);
      setStreaming("");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          className="fixed bottom-6 right-6 z-40 h-12 rounded-full px-5 shadow-lg"
          aria-label={t("askAiTutor")}
        >
          <Sparkles className="h-5 w-5" />
          {t("askAiTutor")}
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[85vh] max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5" />
            {t("socraticTutor")}
          </DialogTitle>
          <DialogDescription>{t("tutorDesc")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="tutor-topic">{t("topic")}</Label>
          <Input
            id="tutor-topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder={t("tutorTopicPlaceholder")}
          />
        </div>

        <div className="min-h-[220px] flex-1 space-y-3 overflow-y-auto rounded-lg border bg-muted/30 p-3">
          {messages.length === 0 && !streaming && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {t("tutorEmpty")}
            </p>
          )}
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={cn(
                "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm",
                message.role === "user"
                  ? "ml-auto rounded-br-sm bg-primary text-primary-foreground"
                  : "rounded-bl-sm bg-background"
              )}
            >
              {message.content}
            </div>
          ))}
          {(streaming || sending) && (
            <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-background px-3.5 py-2 text-sm">
              {streaming || (
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t("tutorThinking")}
                </span>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="flex gap-2">
          <Input
            value={input}
            placeholder={t("tutorPlaceholder")}
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
      </DialogContent>
    </Dialog>
  );
}
