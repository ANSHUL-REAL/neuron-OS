import { Brain } from "lucide-react";

import type { MemoryRecord } from "../types";

interface Props {
  memories: MemoryRecord[];
}

export function MemoryPanel({ memories }: Props) {
  return (
    <section className="panel" aria-label="Memory">
      <div className="panel-heading">
        <h2>Memory</h2>
        <Brain size={17} />
      </div>
      {memories.length === 0 ? (
        <p className="empty">Relevant memories will appear here.</p>
      ) : (
        memories.map((memory) => (
          <article className="memory" key={memory.id}>
            <span>{memory.kind}</span>
            <p>{memory.content}</p>
          </article>
        ))
      )}
    </section>
  );
}
