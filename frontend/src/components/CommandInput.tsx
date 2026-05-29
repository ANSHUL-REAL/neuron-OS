import { Mic, Send, Square, Terminal } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { transcribeAudio } from "../api";
import { VoiceOrb } from "./VoiceOrb";

interface Props {
  disabled: boolean;
  onSubmit: (message: string) => Promise<void>;
}

export function CommandInput({ disabled, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const [voiceStatus, setVoiceStatus] = useState("Ask anything, or tap the mic and speak.");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceLevel, setVoiceLevel] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => () => cleanupAudio(), []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const message = value.trim();
    if (!message) return;
    setValue("");
    await onSubmit(message);
  }

  function cleanupAudio() {
    if (animationRef.current !== null) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (recorderRef.current) {
      recorderRef.current.ondataavailable = null;
      recorderRef.current.onstop = null;
      recorderRef.current = null;
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }
    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setVoiceLevel(0);
  }

  function startVoiceMeter(stream: MediaStream) {
    const AudioContextCtor = window.AudioContext ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextCtor) return;

    const audioContext = new AudioContextCtor();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    const data = new Uint8Array(analyser.frequencyBinCount);

    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.25;
    source.connect(analyser);

    audioContextRef.current = audioContext;
    analyserRef.current = analyser;

    const updateLevel = () => {
      if (!analyserRef.current) return;
      analyserRef.current.getByteFrequencyData(data);
      let sum = 0;
      for (let index = 0; index < data.length; index += 1) {
        const value = data[index] / 255;
        sum += value * value;
      }
      setVoiceLevel(Math.min(Math.sqrt(sum / data.length) * 3, 1));
      animationRef.current = requestAnimationFrame(updateLevel);
    };

    animationRef.current = requestAnimationFrame(updateLevel);
  }

  async function toggleRecording() {
    if (recording && recorderRef.current) {
      setVoiceStatus("Transcribing...");
      setRecording(false);
      setTranscribing(true);
      recorderRef.current.stop();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceStatus("Voice input is not available in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 48000
        }
      });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => chunksRef.current.push(event.data);
      recorder.onstop = async () => {
        try {
          const transcript = await transcribeAudio(new Blob(chunksRef.current, { type: "audio/webm" }));
          const cleanTranscript = transcript.trim();
          setValue(cleanTranscript);
          setVoiceStatus(cleanTranscript ? `Heard: ${cleanTranscript}` : "I did not catch any speech.");
          if (cleanTranscript) {
            await onSubmit(cleanTranscript);
            setValue("");
          }
        } catch (error) {
          setVoiceStatus(error instanceof Error ? error.message : "Voice transcription failed.");
        } finally {
          setTranscribing(false);
          cleanupAudio();
        }
      };

      startVoiceMeter(stream);
      recorder.start();
      recorderRef.current = recorder;
      setVoiceStatus("Listening...");
      setRecording(true);
    } catch (error) {
      cleanupAudio();
      setVoiceStatus(error instanceof Error ? error.message : "Microphone permission was blocked.");
    }
  }

  return (
    <div className="command-wrap">
      <div className="voice-stage-orb">
        <VoiceOrb active={recording} energy={voiceLevel} transcribing={transcribing} />
        <span>{recording ? "System Listening" : transcribing ? "Transcribing" : "Voice Standby"}</span>
      </div>

      <form className="command-input" onSubmit={submit}>
        <Terminal size={19} className="command-terminal-icon" />
        <button
          aria-label={recording ? "Stop voice recording" : "Start voice recording"}
          className={`icon-button ${recording ? "recording" : ""}`}
          disabled={disabled}
          type="button"
          onClick={toggleRecording}
        >
          {recording ? <Square size={18} /> : <Mic size={18} />}
        </button>
        <input
          aria-label="Command"
          disabled={disabled}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask NeuronOS..."
          value={value}
        />
        <button aria-label="Send command" className="send-button" disabled={disabled || !value.trim()} type="submit">
          <Send size={16} />
        </button>
      </form>
      {voiceStatus ? <p className="voice-status">{voiceStatus}</p> : null}
    </div>
  );
}
