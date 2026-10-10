import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Github, Loader2, SendHorizontal } from "lucide-react";
import { analyzeRepository, askQuestion, listRepositories } from "./api.js";
import RepositoryInput from "./components/RepositoryInput.jsx";
import StatusPanel from "./components/StatusPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";

const initialUrl = "https://github.com/openai/openai-python";

export default function App() {
  const [repoUrl, setRepoUrl] = useState(initialUrl);
  const [analysis, setAnalysis] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listRepositories()
      .then(setRepositories)
      .catch(() => setRepositories([]));
  }, []);

  const activeRepository = useMemo(() => {
    if (analysis) {
      return analysis;
    }
    return repositories[0] || null;
  }, [analysis, repositories]);

  async function handleAnalyze(event) {
    event.preventDefault();
    if (!repoUrl.trim() || isAnalyzing) {
      return;
    }

    setIsAnalyzing(true);
    setError("");
    setMessages([]);
    try {
      const result = await analyzeRepository(repoUrl.trim());
      setAnalysis(result);
      setRepositories((current) => [
        {
          repository_id: result.repository_id,
          owner: result.owner,
          repository: result.repository,
          url: repoUrl.trim(),
          files: result.files,
          chunks: result.chunks,
          indexed_at: new Date().toISOString(),
        },
        ...current.filter((item) => item.repository_id !== result.repository_id),
      ]);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    if (!activeRepository || !question.trim() || isAsking) {
      return;
    }

    const userQuestion = question.trim();
    setQuestion("");
    setError("");
    setIsAsking(true);
    setMessages((current) => [...current, { role: "user", content: userQuestion }]);

    try {
      const result = await askQuestion(activeRepository.repository_id, userQuestion);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          sources: result.sources,
        },
      ]);
    } catch (caught) {
      setError(caught.message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "I could not answer that question. Check the repository status and try again.",
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">
          <Github aria-hidden="true" size={22} />
        </div>
        <div>
          <h1>codedive</h1>
        </div>
      </header>

      <main className="workspace">
        <section className="sidebar" aria-label="Repository setup">
          <RepositoryInput
            value={repoUrl}
            onChange={setRepoUrl}
            onSubmit={handleAnalyze}
            isLoading={isAnalyzing}
          />

          <StatusPanel
            repository={activeRepository}
            repositories={repositories}
            isAnalyzing={isAnalyzing}
            onSelectRepository={(repository) => {
              setAnalysis(repository);
              setMessages([]);
              setError("");
            }}
          />
        </section>

        <section className="chat-surface" aria-label="Repository chat">
          {error ? (
            <div className="alert" role="alert">
              <AlertCircle aria-hidden="true" size={18} />
              <span>{error}</span>
            </div>
          ) : activeRepository ? (
            <div className="ready-banner">
              <CheckCircle2 aria-hidden="true" size={18} />
              <span>
                {activeRepository.owner}/{activeRepository.repository} is ready for questions.
              </span>
            </div>
          ) : null}

          <ChatPanel
            messages={messages}
            disabled={!activeRepository || isAnalyzing}
            question={question}
            onQuestionChange={setQuestion}
            onSubmit={handleAsk}
            isAsking={isAsking}
            submitIcon={isAsking ? <Loader2 className="spin" size={18} /> : <SendHorizontal size={18} />}
          />
        </section>
      </main>
    </div>
  );
}
