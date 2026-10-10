const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = body.detail || "Something went wrong. Please try again.";
    throw new Error(message);
  }
  return body;
}

export function analyzeRepository(url) {
  return request("/analyze", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function askQuestion(repositoryId, question) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ repository_id: repositoryId, question }),
  });
}

export function listRepositories() {
  return request("/repositories");
}
