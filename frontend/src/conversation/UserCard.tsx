interface UserCardProps {
  text: string;
}

export function UserCard({ text }: UserCardProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-md border border-border bg-track px-md py-sm">
        <p className="t-body whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}
