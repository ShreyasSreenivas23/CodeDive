import { CheckCircle2, Clock3, Database, FileCode2 } from "lucide-react";

export default function StatusPanel({ repository, repositories, isAnalyzing, onSelectRepository }) {
  return (
    <div className="panel status-panel">
      <div className="panel-heading">
        <Database aria-hidden="true" size={18} />
        <h2>Status</h2>
      </div>

      {isAnalyzing ? (
        <div className="timeline" aria-live="polite">
          <StatusStep label="Repository cloning" active />
          <StatusStep label="Files loading" active />
          <StatusStep label="Chunks and embeddings" active />
          <StatusStep label="Vector index" active />
        </div>
      ) : repository ? (
        <div className="repository-summary">
          <div className="success-line">
            <CheckCircle2 aria-hidden="true" size={18} />
            <span>Repository indexed</span>
          </div>
          <strong>
            {repository.owner}/{repository.repository}
          </strong>
          <dl>
            <div>
              <dt>Files</dt>
              <dd>{repository.files}</dd>
            </div>
            <div>
              <dt>Chunks</dt>
              <dd>{repository.chunks}</dd>
            </div>
          </dl>
        </div>
      ) : (
        <p className="muted">Analyze a public repository to start.</p>
      )}

      {repositories.length > 0 ? (
        <div className="recent-repos">
          <h3>Recent</h3>
          <div className="repo-list">
            {repositories.slice(0, 5).map((item) => (
              <button
                key={item.repository_id}
                type="button"
                onClick={() => onSelectRepository(item)}
                className={repository?.repository_id === item.repository_id ? "selected" : ""}
              >
                <FileCode2 aria-hidden="true" size={16} />
                <span>
                  {item.owner}/{item.repository}
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StatusStep({ label, active }) {
  return (
    <div className="status-step">
      <Clock3 aria-hidden="true" size={16} className={active ? "pulse" : ""} />
      <span>{label}</span>
    </div>
  );
}
