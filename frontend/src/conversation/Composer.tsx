import { ArrowUp, Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";

import { useComposer } from "../state/composer";

import {
  autocompleteCandidates,
  parseInput,
  type ParsedInput,
  type SlashRegistryEntry,
} from "./slashCommands";

interface ComposerProps {
  disabled?: boolean;
  onSubmit: (parsed: ParsedInput) => void;
  placeholder?: string;
}

export function Composer({
  disabled = false,
  onSubmit,
  placeholder = "Ask anything about this company…",
}: ComposerProps) {
  const value = useComposer((s) => s.draft);
  const setValue = useComposer((s) => s.setDraft);
  const clear = useComposer((s) => s.clear);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const candidates = autocompleteCandidates(value);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "/") return;
      const target = e.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      const el = textareaRef.current;
      if (el === null) return;
      e.preventDefault();
      el.focus();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function submit() {
    const parsed = parseInput(value);
    if (parsed.kind === "message" && parsed.text.length === 0) return;
    onSubmit(parsed);
    clear();
  }

  function applyCandidate(c: SlashRegistryEntry) {
    setValue(`${c.label} `);
    textareaRef.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
      return;
    }
    if (e.key === "Tab" && candidates.length > 0) {
      e.preventDefault();
      const first = candidates[0];
      if (first) applyCandidate(first);
    }
  }

  const hasText = value.trim().length > 0;
  const sendDisabled = disabled || !hasText;

  return (
    <div className="bg-surface">
      <div className="mx-auto max-w-reading w-full px-xl pt-md pb-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="relative"
        >
          {candidates.length > 0 && (
            <SlashAutocomplete candidates={candidates} onPick={applyCandidate} />
          )}
          <div className="flex items-end gap-sm rounded-pill border border-border bg-surface focus-within:border-text-primary transition-[border-color] duration-fast pl-md pr-2xs py-2xs">
            <span
              aria-hidden="true"
              className="self-center text-text-tertiary shrink-0"
            >
              <Sparkles size={16} />
            </span>
            <textarea
              ref={textareaRef}
              rows={1}
              disabled={disabled}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="flex-1 resize-none bg-transparent px-xs py-2xs t-body placeholder:text-text-tertiary focus:outline-none max-h-[200px]"
              aria-label="Message composer"
            />
            <button
              type="submit"
              disabled={sendDisabled}
              aria-label="Send message"
              className={[
                "shrink-0 inline-flex items-center justify-center rounded-pill",
                "h-control-md w-control-md transition-[opacity,background-color] duration-fast",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-text-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
                sendDisabled
                  ? "bg-surface-muted text-text-quaternary cursor-not-allowed"
                  : "bg-surface-inverted text-surface hover:opacity-90",
              ].join(" ")}
            >
              <ArrowUp size={16} aria-hidden="true" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SlashAutocomplete({
  candidates,
  onPick,
}: {
  candidates: SlashRegistryEntry[];
  onPick: (c: SlashRegistryEntry) => void;
}) {
  return (
    <div
      role="listbox"
      aria-label="Slash commands"
      className="absolute bottom-full mb-xs w-full rounded-md border border-border bg-surface shadow-sm overflow-hidden"
    >
      {candidates.map((c) => (
        <button
          key={c.name}
          type="button"
          role="option"
          aria-selected="false"
          onClick={() => onPick(c)}
          className="flex w-full items-center justify-between gap-md px-md py-sm hover:bg-surface-muted text-left"
        >
          <span className="t-mono text-md">{c.label}</span>
          <span className="t-small text-text-tertiary truncate">{c.description}</span>
        </button>
      ))}
    </div>
  );
}
