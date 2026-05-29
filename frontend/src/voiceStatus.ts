const FEMALE_VOICE_PRIORITY = [
  "natural",
  "neural",
  "microsoft aria online",
  "microsoft jenny online",
  "microsoft aria",
  "microsoft jenny",
  "microsoft zira",
  "aria",
  "jenny",
  "zira",
  "sara",
  "samantha",
  "female",
  "woman",
  "girl"
];

export function speakTaskStatus(summary: string) {
  if (
    typeof window === "undefined" ||
    !("speechSynthesis" in window) ||
    typeof SpeechSynthesisUtterance === "undefined" ||
    !summary.trim()
  ) {
    return;
  }

  const synth = window.speechSynthesis;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(toSpokenStatus(summary));
  const voice = selectPreferredVoice(synth.getVoices());
  if (voice) {
    utterance.voice = voice;
  }
  utterance.rate = 0.92;
  utterance.pitch = 1.04;
  utterance.volume = 1;
  synth.speak(utterance);
}

export function toSpokenStatus(summary: string): string {
  const clean = summary.trim().replace(/\.$/, "");
  if (/^open /i.test(clean)) {
    return `${clean.replace(/^open\b/i, "Opening")}.`;
  }
  if (/^run /i.test(clean)) {
    return `${clean.replace(/^run\b/i, "Running")}.`;
  }
  if (/^save /i.test(clean)) {
    return `${clean.replace(/^save\b/i, "Saving")}.`;
  }
  return `${clean}.`;
}

function selectPreferredVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices.length) {
    return null;
  }

  const englishVoices = voices.filter((voice) => voice.lang.toLowerCase().startsWith("en"));
  const pool = englishVoices.length ? englishVoices : voices;

  const scored = pool
    .map((voice) => ({ voice, score: scoreVoice(voice) }))
    .sort((a, b) => b.score - a.score);
  if (scored[0]?.score > 0) {
    return scored[0].voice;
  }

  for (const hint of FEMALE_VOICE_PRIORITY) {
    const match = pool.find((voice) => voice.name.toLowerCase().includes(hint));
    if (match) {
      return match;
    }
  }

  return pool[0] ?? null;
}

function scoreVoice(voice: SpeechSynthesisVoice): number {
  const name = voice.name.toLowerCase();
  let score = 0;
  if (name.includes("natural")) score += 8;
  if (name.includes("neural")) score += 7;
  if (name.includes("online")) score += 3;
  if (name.includes("aria")) score += 6;
  if (name.includes("jenny")) score += 6;
  if (name.includes("zira")) score += 4;
  if (name.includes("sara") || name.includes("samantha")) score += 4;
  if (name.includes("female") || name.includes("woman")) score += 3;
  if (name.includes("david") || name.includes("mark") || name.includes("guy")) score -= 5;
  return score;
}
