import {useCallback, useEffect, useState, type ReactNode} from 'react';
import type {Evidence, Mode} from '../types';

export function useResource<T>(loader: () => Promise<T>, dependencies: unknown[] = []) {
  const [data,setData] = useState<T>();
  const [error,setError] = useState('');
  const [loading,setLoading] = useState(true);
  const [version,setVersion] = useState(0);
  const reload = useCallback(() => setVersion(v => v+1),[]);
  useEffect(() => {let active=true;setLoading(true);setError('');setData(undefined);loader().then(value => {if(active)setData(value)}).catch(e => {if(active)setError(e instanceof Error ? e.message : 'Unable to load data')}).finally(() => {if(active)setLoading(false)});return () => {active=false};},[...dependencies,version]);
  return {data,error,loading,reload};
}
export function ErrorBox({message,retry}:{message:string;retry?:()=>void}) {return <div role="alert" className="notice error"><strong>Unable to complete request</strong><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</div>}
export function Empty({children}:{children:ReactNode}) {return <div className="empty">{children}</div>}
export function Loading(){return <div className="empty" role="status"><span className="spinner"/> Loading sourced data…</div>}
export function ModeBadge({mode}:{mode?:Mode}){return <span className={`badge ${mode==='live'?'live':'fixture'}`}>{mode==='live'?'Live provider data':'Demo · synthetic fixtures'}</span>}
export function StatusBadge({status}:{status:string}){return <span className={`badge status-${status}`}>{status.replaceAll('_',' ')}</span>}
export function PageTitle({eyebrow,title,children}:{eyebrow?:string;title:string;children?:ReactNode}){return <header className="page-title"><div><p className="eyebrow">{eyebrow||'STOCKSCOPE / U.S. MARKETS'}</p><h1>{title}</h1></div>{children}</header>}
export function formatNumber(value:unknown,maximumFractionDigits=2){return typeof value==='number' && Number.isFinite(value)?new Intl.NumberFormat('en-US',{maximumFractionDigits}).format(value):'Unavailable'}
export function money(value:unknown,currency='USD'){return typeof value==='number' && Number.isFinite(value)?new Intl.NumberFormat('en-US',{style:'currency',currency}).format(value):'Unavailable'}
export function dateTime(value?:string|null){if(!value)return 'Unavailable';const date=new Date(value);return Number.isNaN(date.valueOf())?value:date.toLocaleString()}
export function Gaps({gaps}:{gaps?:unknown[]}){if(!gaps?.length)return null;return <div className="notice"><strong>Data limitations</strong><ul>{gaps.map((gap,i)=><li key={i}>{typeof gap==='string'?gap:JSON.stringify(gap)}</li>)}</ul></div>}
export function SourceLink({url,name,className}:{url:string;name:string;className?:string}){return /^https?:\/\//i.test(url)?<a className={className} href={url} target="_blank" rel="noreferrer">{name} ↗</a>:<span className={className}>{name}</span>}
export function EvidenceTable({evidence}:{evidence:Evidence[]}){return evidence.length?<div className="table-scroll"><table><thead><tr><th>Evidence / field</th><th>Value / unit</th><th>Period</th><th>Source & publication</th><th>Retrieved</th></tr></thead><tbody>{evidence.map(ev=><tr key={ev.evidence_id}><td><code>{ev.evidence_id}</code><br/>{ev.field.replaceAll('_',' ')}</td><td>{typeof ev.value==='number'?formatNumber(ev.value):ev.value??'Unavailable'} {ev.unit}<small>{ev.currency}</small></td><td>{ev.period}</td><td><SourceLink url={ev.source_url} name={ev.source_name}/><small>{dateTime(ev.published_at)}</small></td><td>{dateTime(ev.fetched_at)}{ev.cached&&<small>Cached provider response</small>}{ev.fixture&&<small>Synthetic fixture</small>}</td></tr>)}</tbody></table></div>:<Empty>No evidence available.</Empty>}
