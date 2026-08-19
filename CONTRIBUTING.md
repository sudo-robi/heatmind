# Contributing to HeatMind

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/sudo-robi/heatmind.git
cd heatmind
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running Tests

```bash
# Full test suite (460 tests)
pytest tests/ -v

# Smoke test
python test_all.py

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

## Code Style

- **Formatter/Linter:** ruff (configured in `pyproject.toml`)
- **Type hints:** encouraged but not enforced
- **Line length:** 120 characters max

```bash
ruff check . --fix
ruff format .
```

## Pull Requests

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and add tests
3. Ensure all tests pass: `pytest tests/ -v`
4. Lint your code: `ruff check .`
5. Commit with a clear message
6. Push and open a PR

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

## License

By contributing, you agree your code will be licensed under MIT.
