import { AISetup } from './components/AIConfiguration';
import { Shell } from './layout/Shell';
import { AppRoutes } from './router';
export function App() {
  return (
    <Shell>
      <AppRoutes />
      <AISetup />
    </Shell>
  );
}
