interface Props {
  logs: string[];
}

export function ExecutionLog({ logs }: Props) {
  return (
    <section className="panel" aria-label="Execution log">
      <div className="panel-heading">
        <h2>Execution</h2>
        <span>{logs.length}</span>
      </div>
      <div className="log-list">
        {logs.length === 0 ? <p className="empty">Tool activity will be logged here.</p> : null}
        {logs.map((log) => (
          <p key={log}>{log}</p>
        ))}
      </div>
    </section>
  );
}
