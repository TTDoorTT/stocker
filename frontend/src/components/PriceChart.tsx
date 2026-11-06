import type {PriceBar} from '../types';
import {dateTime,money,Empty,SourceLink} from './shared';

export function PriceChart({bars,currency}:{bars:PriceBar[];currency:string}){
 const valid=bars.filter(bar=>Number.isFinite(bar.close));if(valid.length<2)return <Empty>Historical prices unavailable. A chart needs at least two sourced observations.</Empty>;
 const min=Math.min(...valid.map(b=>b.close)),max=Math.max(...valid.map(b=>b.close)),span=max-min||1;
 const points=valid.map((b,i)=>`${30+i/(valid.length-1)*840},${170-(b.close-min)/span*140}`).join(' ');
 return <div className="price-chart"><div className="chart-caption"><span>{money(max,currency)}</span><span>Daily close · available observations</span></div><svg viewBox="0 0 900 200" role="img" aria-label={`Closing price history from ${valid[0].date} to ${valid.at(-1)!.date}`}><line x1="30" y1="170" x2="870" y2="170" stroke="currentColor" opacity=".12"/><polyline fill="none" stroke="var(--accent)" strokeWidth="2.5" points={points}/></svg><div className="chart-caption"><span>{dateTime(valid[0].date)}</span><span>{money(min,currency)}</span><span>{dateTime(valid.at(-1)!.date)}</span></div>{valid[0].source_url&&<SourceLink className="source" url={valid[0].source_url} name={valid[0].source_name||'Historical source'}/>}{valid[0].limitations?.map(text=><small key={text}>{text}</small>)}</div>
}
