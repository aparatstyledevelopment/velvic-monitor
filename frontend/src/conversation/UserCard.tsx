interface UserCardProps {
  text: string;
}

export function UserCard({ text }: UserCardProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-lg border border-border-strong bg-surface-sunken px-xl py-xs">
        <p className="t-small text-text-primary whitespace-pre-wrap leading-snug">
          {text}
        </p>
      </div>
    </div>
  );
}
