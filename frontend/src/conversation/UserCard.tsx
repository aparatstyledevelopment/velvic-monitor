interface UserCardProps {
  text: string;
}

export function UserCard({ text }: UserCardProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-lg bg-surface-sunken p-xl">
        <p className="t-small text-text-primary whitespace-pre-wrap leading-snug">
          {text}
        </p>
      </div>
    </div>
  );
}
