// Menu export study plan (PDF / ICS) untuk F-08.
"use client";

import { useState } from "react";
import { CalendarPlus, Download, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { exportApi, getErrorMessage } from "@/lib/api";
import { downloadBlob } from "@/lib/download";

export function ExportMenu({ planId }: { planId: string }) {
  const [busy, setBusy] = useState<"pdf" | "ics" | null>(null);

  const handlePdf = async () => {
    setBusy("pdf");
    try {
      const blob = await exportApi.pdf(planId);
      downloadBlob(blob, `study-plan-${planId}.pdf`);
      toast.success("PDF downloaded.");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const handleIcs = async () => {
    setBusy("ics");
    try {
      const blob = await exportApi.ics(planId);
      downloadBlob(blob, `study-plan-${planId}.ics`);
      toast.success("Calendar file downloaded.");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={busy !== null}>
          {busy !== null ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>Export plan</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="cursor-pointer"
          disabled={busy !== null}
          onClick={handlePdf}
        >
          <FileText className="mr-2 h-4 w-4" />
          Download PDF
        </DropdownMenuItem>
        <DropdownMenuItem
          className="cursor-pointer"
          disabled={busy !== null}
          onClick={handleIcs}
        >
          <CalendarPlus className="mr-2 h-4 w-4" />
          Add to Calendar (.ics)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
