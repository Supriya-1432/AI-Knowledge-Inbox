export default function QueryPanel({
  question,
  setQuestion,
  onSubmit,
  loading,
  answer,
  sources,
  itemCount,
}) {
  return (
    <section className="panel panel-ask">
      <div className="panel-head">
        <h2>Ask your inbox</h2>
        <p>Answers come only from what you’ve saved, with sources shown below.</p>
      </div>

      <div className="panel-body">
        <form className="ask-box" onSubmit={onSubmit}>
          <label className="field-label" htmlFor="question-input">
            Question
          </label>
          <div className="ask-row">
            <input
              id="question-input"
              type="text"
              placeholder={
                itemCount
                  ? "e.g. What does the PPE article say about edge cases?"
                  : "Save something first, then ask a question…"
              }
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
            />
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading || !question.trim()}
            >
              {loading ? "Thinking…" : "Ask"}
            </button>
          </div>
        </form>

        <div className="answer-stage">
          {!answer && !loading && (
            <p className="answer-placeholder">
              Ask a question about your notes and links. We’ll retrieve the most
              relevant pieces and answer with citations.
            </p>
          )}

          {loading && (
            <p className="answer-placeholder">Searching your library and writing an answer…</p>
          )}

          {answer && (
            <>
              <div className="answer-block">
                <h3>Answer</h3>
                <p className="answer-text">{answer}</p>
              </div>

              <div className="sources-block">
                <h3>Sources</h3>
                {sources.length === 0 ? (
                  <p className="hint">No sources returned for this answer.</p>
                ) : (
                  <ul className="source-list">
                    {sources.map((src, idx) => (
                      <li key={`${src.item_id}-${idx}`}>
                        <strong>
                          {src.source_type === "url" ? "Link" : "Note"} · item #{src.item_id}
                        </strong>
                        <span className="source-link">{src.source}</span>
                        <p>{src.snippet}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
