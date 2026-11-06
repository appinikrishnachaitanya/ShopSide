"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

export default function WorkspaceOverlay({ open, title, drawer = false, onClose, children }: {
  open: boolean; title: string; drawer?: boolean; onClose: () => void; children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    else if (!open && element.open) element.close();
  }, [open]);
  useEffect(() => {
    if (open) dialog.current?.querySelector<HTMLButtonElement>(".workspace-dialog-header button")?.focus();
  }, [open, title]);
  return <dialog ref={dialog} className={"workspace-dialog" + (drawer ? " workspace-drawer" : "")}
    aria-label={title} onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="workspace-dialog-inner">
      <header className="workspace-dialog-header"><span>{title}</span><button type="button" onClick={onClose} aria-label={`Close ${title}`}>×</button></header>
      {children}
    </div>
  </dialog>;
}
