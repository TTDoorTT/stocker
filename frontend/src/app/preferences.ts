const HIDE_INDUSTRY_KEY = 'stocker-hide-industry-research';
export const WORKSPACE_PREFS_EVENT = 'workspace-preferences-changed';

export function isIndustryResearchHidden(): boolean {
  try {
    return window.localStorage.getItem(HIDE_INDUSTRY_KEY) === 'true';
  } catch {
    return false;
  }
}

export function setIndustryResearchHidden(hidden: boolean): void {
  try {
    if (hidden) {
      window.localStorage.setItem(HIDE_INDUSTRY_KEY, 'true');
    } else {
      window.localStorage.removeItem(HIDE_INDUSTRY_KEY);
    }
  } catch {
    // Workspace preferences still apply for the session if browser storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent(WORKSPACE_PREFS_EVENT, { detail: { hideIndustryResearch: hidden } }));
}
