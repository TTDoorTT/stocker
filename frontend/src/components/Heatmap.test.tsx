import {act,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {Heatmap} from './Heatmap';

beforeEach(()=>vi.useFakeTimers());
afterEach(()=>vi.useRealTimers());
function status(frame:HTMLIFrameElement,value:string,attempt=0){
  fireEvent(window,new MessageEvent('message',{source:frame.contentWindow,data:{type:'stockscope-heatmap-status',attempt,status:value}}));
}

describe('isolated TradingView lifecycle',()=>{
  it('keeps the external script outside the app document and restricts its sandbox',()=>{
    render(<Heatmap/>);
    const frame=screen.getByTitle('TradingView heatmap sandbox') as HTMLIFrameElement;
    expect(frame).toHaveAttribute('sandbox','allow-scripts allow-same-origin');
    expect(frame).not.toHaveAttribute('srcdoc');
    expect(frame.src).toMatch(/^data:text\/html/);
    expect(decodeURIComponent(frame.src)).toContain('embed-widget-stock-heatmap.js');
    expect(document.querySelector('script[src*="tradingview"]')).toBeNull();
    expect(decodeURIComponent(frame.src)).toContain("frame.addEventListener('load'");
  });

  it('does not treat outer load or unrelated messages as widget confirmation',()=>{
    render(<Heatmap/>);
    const frame=screen.getByTitle('TradingView heatmap sandbox') as HTMLIFrameElement;
    fireEvent.load(frame);
    fireEvent(window,new MessageEvent('message',{data:{type:'stockscope-heatmap-status',attempt:0,status:'loaded'}}));
    act(()=>vi.advanceTimersByTime(20000));
    expect(screen.getByText(/could not be confirmed loaded/)).toBeInTheDocument();
  });

  it('accepts only current-frame confirmation and clears pending resources on unmount',()=>{
    const view=render(<Heatmap/>);
    const frame=screen.getByTitle('TradingView heatmap sandbox') as HTMLIFrameElement;
    status(frame,'loaded');
    act(()=>vi.advanceTimersByTime(20000));
    expect(screen.queryByText(/could not be confirmed loaded/)).not.toBeInTheDocument();
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
    expect(document.querySelector('iframe')).toBeNull();
  });

  it('retries in a fresh document and ignores stale-frame responses',()=>{
    const view=render(<Heatmap/>);
    const oldFrame=screen.getByTitle('TradingView heatmap sandbox') as HTMLIFrameElement;
    status(oldFrame,'failed');
    fireEvent.click(screen.getByRole('button',{name:'Reload heatmap'}));
    const frame=screen.getByTitle('TradingView heatmap sandbox') as HTMLIFrameElement;
    expect(frame).not.toBe(oldFrame);
    status(frame,'loaded',0);
    act(()=>vi.advanceTimersByTime(20000));
    expect(screen.getByText(/could not be confirmed loaded/)).toBeInTheDocument();
    status(frame,'loaded',1);
    expect(screen.queryByText(/could not be confirmed loaded/)).not.toBeInTheDocument();
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
