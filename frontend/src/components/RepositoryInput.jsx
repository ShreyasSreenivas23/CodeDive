import { GitBranch, Loader2, Search } from "lucide-react";

export default function RepositoryInput({ value, onChange, onSubmit, isLoading }) {
  return (
    <form className="repo-form panel" onSubmit={onSubmit}>
      <div className="panel-heading">
        <GitBranch aria-hidden="true" size={18} />
        <h2>Repository</h2>
      </div>

      <label htmlFor="repository-url">GitHub URL</label>
      <div className="input-row">
        <input
          id="repository-url"
          type="url"
          placeholder="https://github.com/user/project"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !value.trim()} title="Analyze repository">
          {isLoading ? <Loader2 className="spin" aria-hidden="true" size={18} /> : <Search aria-hidden="true" size={18} />}
          <span>Analyze</span>
        </button>
      </div>
    </form>
  );
}
