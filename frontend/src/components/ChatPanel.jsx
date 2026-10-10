import { Bot, MessageSquareText, UserRound } from "lucide-react";
import SourceList from "./SourceList.jsx";

export default function ChatPanel({
  messages,
  disabled,
  question,
  onQuestionChange,
  onSubmit,
  isAsking,
  submitIcon,
}) {
  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div>
          <MessageSquareText aria-hidden="true" size={20} />
          <h2>Questions</h2>
        </div>
      </div>

      <div className="messages" aria-live="polite">
        {messages.length === 0 ? (
          <div className="empty-state">
            <Bot aria-hidden="true" size={30} />
            <p>No questions yet.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={`message ${message.role} ${message.isError ? "error" : ""}`}>
              <div className="avatar" aria-hidden="true">
                {message.role === "user" ? <UserRound size={17} /> : <Bot size={17} />}
              </div>
              <div className="bubble">
                <p>{message.content}</p>
                {message.sources?.length ? <SourceList sources={message.sources} /> : null}
              </div>
            </article>
          ))
        )}
      </div>

      <form className="chat-input" onSubmit={onSubmit}>
        <textarea
          rows={3}
          placeholder={disabled ? "Analyze a repository first" : "Ask about the repository"}
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          disabled={disabled || isAsking}
        />
        <button type="submit" disabled={disabled || isAsking || !question.trim()} title="Ask question">
          {submitIcon}
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
}
