function formatWhen(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function ItemList({ items }) {
  if (items.length === 0) {
    return (
      <p className="library-empty">
        Your library is empty. Add a note or link above — then ask anything about it.
      </p>
    );
  }

  return (
    <div className="library" aria-label="Saved items">
      {items.map((item) => {
        const title =
          item.source_type === "url" ? item.source : `Note #${item.id}`;
        return (
          <article key={item.id} className="library-item">
            <div className="library-item-top">
              <span className="badge">
                {item.source_type === "url" ? "Link" : "Note"}
              </span>
              <span className="library-meta">{formatWhen(item.created_at)}</span>
            </div>
            <p className="library-title">{title}</p>
            <p className="library-preview">{item.preview}</p>
          </article>
        );
      })}
    </div>
  );
}
