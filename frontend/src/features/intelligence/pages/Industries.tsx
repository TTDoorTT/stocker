import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { intelligenceApi } from '../api';

export function Industries() {
  const industries = useResource(() => intelligenceApi.industries());
  return (
    <>
      <PageTitle title="Industry research" />
      <p className="muted">
        Open a guided workspace for each industry. AI Computing Overview has a limited, source-backed research
        pilot; other sections are methodologies until their data integrations are complete.
      </p>
      {industries.loading ? (
        <Loading />
      ) : industries.error ? (
        <ErrorBox message={industries.error} retry={industries.reload} />
      ) : industries.data?.length ? (
        <div className="industry-grid">
          {industries.data.map((industry) => (
            <article className="panel" key={industry.slug}>
              <p className="eyebrow">INDUSTRY WORKSPACE</p>
              <h2>{industry.name}</h2>
              <p className="muted">
                {industry.slug === 'ai-computing'
                  ? 'Source-backed Overview pilot available'
                  : 'Guided research sections; no verified industry-wide report yet'}
              </p>
              <Link className="button secondary" to={`/industries/${industry.slug}`}>
                Open workspace ↗
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <Empty>Industry templates are unavailable.</Empty>
      )}
    </>
  );
}
