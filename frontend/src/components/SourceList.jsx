import { FileText } from "lucide-react";

export default function SourceList({ sources }) {
  return (
    <div className="sources">
      <h3>Sources</h3>
      <ul>
        {sources.map((source, index) => (
          <li key={`${source.file}-${source.start_line}-${source.end_line}-${index}`}>
            <FileText aria-hidden="true" size={15} />
            <span>{formatSource(source)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatSource(source) {
  if (source.start_line && source.end_line) {
    return `${source.file}:${source.start_line}-${source.end_line}`;
  }
  return source.file;
}
