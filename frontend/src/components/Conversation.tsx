import { Sparkles, UserRound } from "lucide-react";

import type { ConversationMessage } from "../types";

interface Props {
  messages: ConversationMessage[];
}

export function Conversation({ messages }: Props) {
  return (
    <section className="conversation" aria-label="Conversation">
      {messages.map((message) => (
        <article className={`message ${message.role}`} key={message.id}>
          <div className="message-avatar" aria-hidden="true">
            {message.role === "assistant" ? <Sparkles size={17} /> : <UserRound size={17} />}
          </div>
          <div className="message-content">
            <span>{message.role === "assistant" ? "NEURON" : message.role}</span>
            <MessageBody message={message} />
          </div>
        </article>
      ))}
    </section>
  );
}

function MessageBody({ message }: { message: ConversationMessage }) {
  const view = formatMessage(message);

  return (
    <div className="message-body">
      {view.title ? <strong className="message-title">{view.title}</strong> : null}
      {view.lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
    </div>
  );
}

function formatMessage(message: ConversationMessage): { title?: string; lines: string[] } {
  const content = message.content.trim();

  if (message.role === "assistant" && content.startsWith("Done: ")) {
    return {
      title: "Completed",
      lines: [content.replace(/^Done:\s*/, "").trim()]
    };
  }

  if (message.role === "assistant" && /^Opening\b/i.test(content)) {
    return {
      title: "In Progress",
      lines: [content]
    };
  }

  if (message.role === "assistant" && /^Ready\./i.test(content)) {
    return {
      title: "Ready",
      lines: [content.replace(/^Ready\.\s*/, "").trim() || content]
    };
  }

  if (message.role === "system" && /^Safe Mode/i.test(content)) {
    return {
      title: "Safe Mode",
      lines: [content]
    };
  }

  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  return { lines: lines.length ? lines : [content] };
}
