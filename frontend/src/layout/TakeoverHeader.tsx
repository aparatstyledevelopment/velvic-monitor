import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface TakeoverHeaderProps {
  title: string;
  subtitle?: string;
  backTo?: string;
}

export function TakeoverHeader({
  title,
  subtitle,
  backTo = "/",
}: TakeoverHeaderProps) {
  const navigate = useNavigate();
  return (
    <header className="px-xl pt-xl pb-lg max-w-[760px] mx-auto w-full">
      <button
        type="button"
        onClick={() => navigate(backTo)}
        className="inline-flex items-center gap-xs t-small text-text-secondary hover:text-text-primary transition-colors mb-lg"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Back
      </button>
      <h1 className="t-display">{title}</h1>
      {subtitle !== undefined && (
        <p className="t-small text-text-secondary mt-xs">{subtitle}</p>
      )}
    </header>
  );
}
