import { useCallback, useEffect, useState } from "react";
import { getItems, ingestItem, queryKnowledge } from "./api";
import IngestForm from "./components/IngestForm";
import ItemList from "./components/ItemList";
import QueryPanel from "./components/QueryPanel";

function looksLikeUrl(value) {
  const v = value.trim();
  if (!v) return false;
  try {
    const withScheme = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(v) ? v : `https://${v}`;
    const parsed = new URL(withScheme);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export default function App() {
  const [items, setItems] = useState([]);
  const [ingestType, setIngestType] = useState("note");
  const [ingestContent, setIngestContent] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [error, setError] = useState("");

  const refreshItems = useCallback(async () => {
    const data = await getItems();
    setItems(data);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await refreshItems();
      } catch (err) {
        setError(err.message || "Backend not reachable. Is FastAPI running on port 8000?");
      }
    })();
  }, [refreshItems]);

  async function handleIngest(event) {
    event.preventDefault();
    setError("");

    if (ingestType === "url" && !looksLikeUrl(ingestContent)) {
      setError("Please enter a valid http/https URL.");
      return;
    }

    setIngestLoading(true);
    try {
      await ingestItem({ type: ingestType, content: ingestContent });
      setIngestContent("");
      await refreshItems();
    } catch (err) {
      setError(err.message || "Could not save that item.");
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleQuery(event) {
    event.preventDefault();
    setError("");
    setQueryLoading(true);
    setAnswer(null);
    setSources([]);
    try {
      const data = await queryKnowledge(question);
      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (err) {
      setError(err.message || "Could not answer that question.");
    } finally {
      setQueryLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1 className="brand">Knowledge Inbox</h1>
          <p className="brand-note">
            Capture notes and links, then ask questions grounded in what you saved.
          </p>
        </div>
        <span className="count-chip">
          {items.length} {items.length === 1 ? "item" : "items"} saved
        </span>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="workspace">
        <section className="panel">
          <div className="panel-head">
            <h2>Library</h2>
            <p>Add knowledge here. Everything you save can be searched later.</p>
          </div>
          <div className="panel-body">
            <IngestForm
              ingestType={ingestType}
              setIngestType={setIngestType}
              ingestContent={ingestContent}
              setIngestContent={setIngestContent}
              onSubmit={handleIngest}
              loading={ingestLoading}
            />
            <ItemList items={items} />
          </div>
        </section>

        <QueryPanel
          question={question}
          setQuestion={setQuestion}
          onSubmit={handleQuery}
          loading={queryLoading}
          answer={answer}
          sources={sources}
          itemCount={items.length}
        />
      </div>
    </div>
  );
}
