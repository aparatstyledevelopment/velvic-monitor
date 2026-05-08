import { useEffect, useRef, useState } from "react";

import { Button } from "../design/primitives";

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
  placeholder = "Ask why a number moved…",
}: ComposerProps) {
  const [value, setValue] = useState("");
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
    setValue("");
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

  return (
    <div className="border-t border-border bg-surface">
      <div className="mx-auto max-w-[720px] w-full px-lg py-md">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="relative flex flex-col gap-sm"
        >
          {candidates.length > 0 && (
            <SlashAutocomplete candidates={candidates} onPick={applyCandidate} />
          )}
          <div className="flex items-end gap-sm rounded-md border border-border bg-surface focus-within:border-text-primary transition-[border-color] duration-fast">
            <textarea
              ref={textareaRef}
              rows={1}
              disabled={disabled}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="flex-1 resize-none bg-transparent px-md py-sm t-body placeholder:text-text-tertiary focus:outline-none"
              aria-label="Message composer"
            />
            <div className="p-xs">
              <Button
                type="submit"
                size="sm"
                disabled={disabled || value.trim().length === 0}
              >
                Send
              </Button>
            </div>
          </div>
          <p className="t-meta">
            Enter to send · Shift+Enter for newline · / for commands
          </p>
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
      className="absolute bottom-full mb-xs w-full rounded-md border border-border bg-surface shadow-md"
    >
      {candidates.map((c) => (
        <button
          key={c.name}
          type="button"
          role="option"
          aria-selected="false"
          onClick={() => onPick(c)}
          className="flex w-full items-center justify-between gap-md px-md py-sm hover:bg-track text-left"
        >
          <span className="t-mono text-[13px]">{c.label}</span>
          <span className="t-small text-text-tertiary truncate">{c.description}</span>
        </button>
      ))}
    </div>
  );
}
