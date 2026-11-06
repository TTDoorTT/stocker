import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { type AIStatus, appApi } from '../api';
import { AIForm, AISetup } from './AIConfiguration';

const initial: AIStatus = {
  base_url: 'http://127.0.0.1:4000/v1',
  model_id: 'existing',
  has_api_key: true,
  configured: true,
  source: 'saved',
};
beforeEach(() => {
  vi.restoreAllMocks();
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
  };
});
it('tests before saving, preserves omitted keys and clears entered keys after save', async () => {
  const probe = vi.spyOn(appApi, 'testAI').mockResolvedValue({ ok: true, message: 'Connected' });
  const save = vi.spyOn(appApi, 'saveAI').mockResolvedValue(initial);
  render(<AIForm initial={initial} onSaved={vi.fn()} />);
  expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Test Connection' }));
  await screen.findByText('Connected');
  expect(probe).toHaveBeenCalledWith({
    base_url: initial.base_url,
    model_id: initial.model_id,
    api_key: null,
  });
  fireEvent.change(screen.getByLabelText('API Key'), { target: { value: 'new-secret' } });
  expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Test Connection' }));
  await screen.findByText('Connected');
  fireEvent.click(screen.getByRole('button', { name: 'Save' }));
  await screen.findByText('Saved. New requests use these settings.');
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ api_key: 'new-secret' }));
  expect(screen.getByLabelText('API Key')).toHaveValue('');
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
it('does not transfer a saved key to a changed endpoint and exposes test failures', async () => {
  vi.spyOn(appApi, 'testAI').mockResolvedValue({ ok: false, message: 'HTTP 401' });
  render(<AIForm initial={initial} onSaved={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('API Base URL'), { target: { value: 'https://other.example/v1' } });
  expect(screen.getByRole('button', { name: 'Test Connection' })).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Test Connection' }));
  await screen.findByText('HTTP 401');
  expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
});
it('restores environment configuration', async () => {
  const callback = vi.fn();
  const env = { ...initial, source: 'environment' as const };
  vi.spyOn(appApi, 'resetAI').mockResolvedValue(env);
  render(<AIForm initial={initial} onSaved={callback} />);
  fireEvent.click(screen.getByRole('button', { name: 'Use environment configuration' }));
  await waitFor(() => expect(callback).toHaveBeenCalledWith(env));
});
it('opens setup only for an unconfigured model and allows skipping', async () => {
  vi.spyOn(appApi, 'ai').mockResolvedValue({ ...initial, configured: false, model_id: '' });
  render(<AISetup />);
  const dialog = await screen.findByRole('dialog');
  expect(dialog).toHaveAttribute('open');
  fireEvent.click(screen.getByRole('button', { name: 'Skip AI setup' }));
  await waitFor(() => expect(dialog).not.toHaveAttribute('open'));
});
it('does not open initial setup for an existing environment model', async () => {
  const get = vi.spyOn(appApi, 'ai').mockResolvedValue(initial);
  render(<AISetup />);
  await waitFor(() => expect(get).toHaveBeenCalled());
  expect(screen.queryByRole('dialog')).toBeNull();
});
