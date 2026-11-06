import { NavLink, Route, Routes } from 'react-router-dom';
import { DailyReview } from '../features/intelligence/pages/DailyReview';
import { Industries } from '../features/intelligence/pages/Industries';
import { NewsRadar } from '../features/intelligence/pages/NewsRadar';
import { Home } from '../features/market/pages/HomePage';
import { StockPage } from '../features/market/pages/StockPage';
import { MyStocks } from '../features/portfolio/pages/MyStocksPage';
import { ResearchRecords } from '../features/research/pages/Records';
import { ResearchLanding } from '../features/research/pages/ResearchLanding';
import { ResearchRun } from '../features/research/pages/RunDetail';
import { PageTitle } from '../shared/ui/Presentation';
import { Settings } from './pages/SettingsPage';
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/research" element={<ResearchLanding />} />
      <Route path="/stocks/:symbol" element={<StockPage />} />
      <Route path="/runs/:id" element={<ResearchRun />} />
      <Route path="/records" element={<ResearchRecords />} />
      <Route path="/my-stocks" element={<MyStocks />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/daily-review" element={<DailyReview />} />
      <Route path="/intelligence" element={<NewsRadar />} />
      <Route path="/industries" element={<Industries />} />
      <Route
        path="*"
        element={
          <>
            <PageTitle title="Page not found" />
            <NavLink to="/">Return home</NavLink>
          </>
        }
      />
    </Routes>
  );
}
