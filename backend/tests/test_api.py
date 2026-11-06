from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.repository import Repository
from app.main import create_app


def test_local_workflow_and_persistence(tmp_path):
    settings = Settings(_env_file=None, database_url=f'sqlite:///{tmp_path}/demo.db')
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/health').json()['mode'] == 'fixtures'
        assert client.get('/api/stocks/search?q=apple').json()[0]['symbol'] == 'AAPL'
        assert client.get('/api/stocks/AAPL').json()['quote']['fixture']
        assert client.get('/api/stocks/TSX:SHOP').status_code == 422
        assert client.get('/api/stocks/AAPL?market=CA').status_code == 422
        assert client.get('/api/stocks/AAPL/history?range=bad').status_code == 422
        assert client.get('/api/stocks/ZZZZZ').status_code == 503
        assert client.post('/api/watchlist', json={'symbol': 'aapl'}).status_code == 201
        assert client.get('/api/watchlist').json() == [{'symbol': 'AAPL'}]
        assert client.post('/api/positions', json={'symbol': 'AAPL', 'shares': 2,
                                                 'average_cost': 100}).status_code == 201
        position = client.get('/api/positions').json()[0]
        price = client.get('/api/stocks/AAPL').json()['quote']['price']
        assert position['unrealized_pnl'] == 2 * (price - 100)
        assert client.post('/api/positions', json={'symbol': 'AAPL', 'shares': -1,
                                                 'average_cost': 100}).status_code == 422
        assert client.post('/api/positions', json={'symbol': 'AAPL', 'shares': 1,
                                                 'average_cost': 100, 'currency': 'CAD'}).status_code == 422
        assert client.post('/api/chat', json={'symbol': 'AAPL', 'message': 'Explain earnings'}).status_code == 200
        assert client.get('/api/research-runs').json() == []  # chat never launches research
        assert len(client.get('/api/industries').json()) == 20
        assert client.get('/api/intelligence/signals').json()['items'][0]['value'] is None
        assert client.post('/api/intelligence/news/summary').status_code == 503
        assert 'ETF' in client.get('/api/daily-review').json()['coverage']
        launched = client.post('/api/research-runs', json={'symbol': 'NVDA',
                                                         'industry_slug': 'ai-computing'})
        assert launched.status_code == 202
        run_id = launched.json()['run_id']
        import time
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            saved = client.get('/api/research-runs/' + run_id).json()
            if saved['status'] not in ('queued', 'running'):
                break
            time.sleep(0.01)
        assert saved['status'] == 'incomplete'
        assert len(saved['stages']) == 6
        assert saved['industry']['slug'] == 'ai-computing'
        assert client.get('/api/research-runs/' + run_id + '/report').status_code == 200
        assert client.get('/api/research-runs/' + run_id + '/events').json()[-1]['event'] == 'run_finished'
        assert client.get('/api/research-runs/missing').status_code == 422
        assert client.get('/api/research-runs/00000000-0000-0000-0000-000000000001').status_code == 404
        assert client.post('/api/watchlist', json={'symbol': 'MSFT'},
                           headers={'origin': 'https://untrusted.example'}).status_code == 403
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/api/watchlist').json() == [{'symbol': 'AAPL'}]
        assert len(restarted.get('/api/positions').json()) == 1
        assert restarted.get('/api/research-runs/' + run_id).json()['report'] == saved['report']


def test_research_restart_marks_interrupted(tmp_path):
    settings = Settings(_env_file=None)
    repository = Repository(f'sqlite:///{tmp_path}/runs.db')
    from app.orchestrator.engine import new_run
    run = new_run('AAPL', settings)
    repository.save_run(run)
    with TestClient(create_app(settings, repo=repository)) as client:
        restored = client.get('/api/research-runs/' + run['run_id']).json()
        assert restored['status'] == 'incomplete'
        assert 'restart' in restored['gaps'][0]
