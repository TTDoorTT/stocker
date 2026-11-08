import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './app/App';
import './styles/global.css';
import './styles/themes.css';
import './styles/rss.css';
import './styles/stock-chart.css';
import './styles/quarterly-trends.css';
import './styles/earnings.css';
import './styles/event-study.css';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
