export default function IngestForm({
  ingestType,
  setIngestType,
  ingestContent,
  setIngestContent,
  onSubmit,
  loading,
}) {
  return (
    <form className="composer" onSubmit={onSubmit}>
      <div className="segmented" role="tablist" aria-label="Content type">
        <button
          type="button"
          className={ingestType === "note" ? "active" : ""}
          onClick={() => setIngestType("note")}
        >
          Write a note
        </button>
        <button
          type="button"
          className={ingestType === "url" ? "active" : ""}
          onClick={() => setIngestType("url")}
        >
          Save a link
        </button>
      </div>

      {ingestType === "note" ? (
        <>
          <label className="field-label" htmlFor="note-input">
            Note
          </label>
          <textarea
            id="note-input"
            rows={5}
            placeholder="Ideas, meeting notes, definitions — anything you want to ask about later."
            value={ingestContent}
            onChange={(e) => setIngestContent(e.target.value)}
            required
          />
        </>
      ) : (
        <>
          <label className="field-label" htmlFor="url-input">
            Page URL
          </label>
          <input
            id="url-input"
            type="url"
            placeholder="https://example.com/article"
            value={ingestContent}
            onChange={(e) => setIngestContent(e.target.value)}
            required
          />
          <p className="hint">We’ll pull the readable text from public http/https pages.</p>
        </>
      )}

      <div className="composer-actions">
        <p className="hint">
          {ingestType === "note" ? "Saved notes become searchable." : "Links are indexed for Q&A."}
        </p>
        <button
          className="btn btn-primary"
          type="submit"
          disabled={loading || !ingestContent.trim()}
        >
          {loading
            ? ingestType === "url"
              ? "Reading page…"
              : "Saving…"
            : ingestType === "url"
              ? "Add link"
              : "Add note"}
        </button>
      </div>
    </form>
  );
}
