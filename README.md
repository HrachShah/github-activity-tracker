# GitHub Activity Tracker

A Python CLI tool for tracking and analyzing GitHub repository activity — commits, stars, forks, issues, and PRs over time.

## Features

- **Track repository metrics** — monitor commits, stars, forks, open issues/PRs
- **Multiple output formats** — JSON, CSV, and human-readable text
- **Rate-limit aware** — uses GitHub token authentication, handles 429s gracefully
- **Configurable tracking** — track specific repos or search by criteria (language, stars, etc.)
- **Historical snapshots** — store snapshots in SQLite for trend analysis
- **Alerting** — configurable thresholds for activity drops or spikes

## Installation

```bash
pip install github-activity-tracker
```

Or from source:

```bash
git clone https://github.com/HrachShah/github-activity-tracker.git
cd github-activity-tracker
pip install -e .
```

## Quick Start

Track a single repository:

```bash
gh-activity track HrachShah/FreeRelay
```

Track multiple repositories from a file:

```bash
gh-activity track --input repos.txt
```

View activity report:

```bash
gh-activity report HrachShah/FreeRelay --days 30
```

Export to JSON:

```bash
gh-activity report HrachShah/FreeRelay --format json --output report.json
```

## Configuration

Set your GitHub token (optional, but increases rate limits):

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

Or use the `--token` flag:

```bash
gh-activity track HrachShah/FreeRelay --token ghp_xxxxxxxxxxxx
```

## Commands

### `track`

Track activity for one or more repositories.

```bash
gh-activity track [OPTIONS] REPOS...
```

**Options:**
- `--input FILE` — Read repositories from a file (one per line)
- `--days N` — Number of days of history to fetch (default: 30)
- `--output FORMAT` — Output format: `text`, `json`, `csv` (default: `text`)
- `--token TOKEN` — GitHub personal access token

### `report`

Generate an activity report for a repository.

```bash
gh-activity report REPO [OPTIONS]
```

**Options:**
- `--days N` — Number of days to analyze (default: 30)
- `--format FORMAT` — Output format: `text`, `json`, `csv` (default: `text`)
- `--output FILE` — Write output to file instead of stdout

### `snapshot`

Save a snapshot of current repository state to the database.

```bash
gh-activity snapshot REPOS...
```

### `list`

List all tracked repositories.

```bash
gh-activity list
```

### `trend`

Show activity trends over time.

```bash
gh-activity trend REPO --days 90
```

## Project Structure

```
github-activity-tracker/
├── src/
│   └── gh_activity_tracker/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point
│       ├── tracker.py      # Core tracking logic
│       ├── github_api.py   # GitHub API interactions
│       ├── storage.py      # SQLite storage
│       └── formatters/     # Output formatters
├── tests/
│   ├── test_tracker.py
│   ├── test_github_api.py
│   └── test_storage.py
├── README.md
├── LICENSE
└── pyproject.toml
```

## License

MIT License — see [LICENSE](LICENSE) file for details.

## Related Tools

- [gh CLI](https://github.com/cli/cli) — Official GitHub CLI
- [gitstal](https://github.com/$unknown/gitstal) — GitHub stature analyzer
- [github-activity-stats](https://github.com/$unknown/github-activity-stats) — Activity visualization

## Contributing

Contributions welcome! Please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request