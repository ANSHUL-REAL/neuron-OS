interface Props {
  active: boolean;
  energy: number;
  transcribing: boolean;
}

export function VoiceOrb({ active, energy, transcribing }: Props) {
  const scale = (1 + Math.min(Math.max(energy, 0), 1) * 0.12).toFixed(3);

  return (
    <div
      aria-label="Voice orb"
      className={`voice-orb ${active ? "active" : ""} ${transcribing ? "transcribing" : ""}`}
      role="img"
      style={{ ["--orb-energy" as string]: scale }}
    >
      <div className="orb-ring-outer" />
      <div className="orb-ring-mid" />
      <div className="orb-core" />
    </div>
  );
}
