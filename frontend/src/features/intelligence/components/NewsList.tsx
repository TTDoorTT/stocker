import type { NewsItem } from '../../../shared/types';
import { Empty } from '../../../shared/ui/Feedback';
import { SourceLink } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';

export function NewsList({ items }: { items: NewsItem[] }) {
  return items.length ? (
    <div className="news-list">
      {items.map((item, i) => (
        <article key={i}>
          <SourceLink url={item.source_url} name={item.headline} />
          <small>
            {item.source_name} · {dateTime(item.published_at)}
            {item.symbols?.length ? ` · ${item.symbols.join(', ')}` : ''}
            {item.cached ? ' · cached' : ''}
          </small>
          {item.fetched_at && <small>Retrieved {dateTime(item.fetched_at)}</small>}
          {item.summary && <p>{item.summary}</p>}
        </article>
      ))}
    </div>
  ) : (
    <Empty>No headlines available from configured sources.</Empty>
  );
}
