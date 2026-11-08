import type { IssuerFinding, IssuerFindingCitation } from '../types';

const SEC_DOCUMENT =
  /^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/[1-9][0-9]*\/[0-9]{18}\/[A-Za-z0-9_.-]{1,180}\.(?:htm|html|txt)$/i;

function CitedSources({ citations }: { citations: IssuerFindingCitation[] }) {
  return (
    <ul>
      {citations.map((citation, index) => (
        <li key={`${citation.evidence_id}-${index}`}>
          <code>{citation.evidence_id}</code>{' '}
          {SEC_DOCUMENT.test(citation.source_url) ? (
            <a href={citation.source_url} target="_blank" rel="noopener noreferrer">
              SEC filing ({citation.symbol})
            </a>
          ) : (
            <span>Source link unavailable</span>
          )}
        </li>
      ))}
    </ul>
  );
}

export function IssuerFindings({ findings }: { findings?: IssuerFinding[] }) {
  if (!findings?.length) return null;

  const singles = findings
    .filter((finding) => finding.scope === 'single_issuer' && finding.issuers.length === 1)
    .sort((left, right) => left.issuers[0].localeCompare(right.issuers[0]));

  const multiple = findings.filter(
    (finding) => finding.scope === 'multiple_issuers' && finding.issuers.length > 1,
  );

  if (!singles.length && !multiple.length) return null;

  return (
    <section aria-label="Issuer-attributed findings">
      <h3>Issuer-attributed findings</h3>
      <p className="muted">
        Model-screened disclosures from selected SEC issuers; not independent verification or a ranked issuer
        comparison.
      </p>

      {singles.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Issuer</th>
                <th>Reviewed claim</th>
                <th>Cited SEC evidence</th>
              </tr>
            </thead>
            <tbody>
              {singles.map((finding) => (
                <tr key={finding.claim_index}>
                  <td>
                    <strong>{finding.issuers[0]}</strong>
                  </td>
                  <td>{finding.text}</td>
                  <td>
                    <CitedSources citations={finding.citations} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {multiple.length > 0 && (
        <div>
          <h4>Multiple-issuer citations — not verified comparisons</h4>
          <p className="muted">
            Citing several issuers does not establish relative performance or a relationship between those
            companies.
          </p>

          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Issuers cited</th>
                  <th>Reviewed claim</th>
                  <th>Cited SEC evidence</th>
                </tr>
              </thead>
              <tbody>
                {multiple.map((finding) => (
                  <tr key={finding.claim_index}>
                    <td>{finding.issuers.join(', ')}</td>
                    <td>{finding.text}</td>
                    <td>
                      <CitedSources citations={finding.citations} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
