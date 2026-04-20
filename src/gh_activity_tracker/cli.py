"""CLI entry point for GitHub Activity Tracker."""

import argparse
import sys
from typing import Annotated

from .formatters import format_csv, format_json, format_text
from .storage import ActivityStorage
from .tracker import ActivityTracker


def cmd_track(args: argparse.Namespace) -> None:
    """Handle the track command."""
    tracker = ActivityTracker(token=args.token)
    storage = ActivityStorage() if args.save else None

    if args.input:
        with open(args.input, "r") as f:
            repos = [line.strip() for line in f if line.strip()]
    else:
        repos = args.repos

    results = tracker.track_multiple(repos, days=args.days)
    output = format_json(results) if args.format == "json" else format_csv(results) if args.format == "csv" else format_text(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)

    if storage:
        for activity in results:
            storage.save_snapshot(activity)
        for repo in repos:
            storage.add_tracked_repo(repo)
        print("Snapshots saved to database.")


def cmd_report(args: argparse.Namespace) -> None:
    """Handle the report command."""
    tracker = ActivityTracker(token=args.token)
    activity = tracker.track_repo(args.repo, days=args.days)
    results = [activity] if activity else []
    output = format_json(results) if args.format == "json" else format_csv(results) if args.format == "csv" else format_text(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


def cmd_snapshot(args: argparse.Namespace) -> None:
    """Handle the snapshot command."""
    tracker = ActivityTracker(token=args.token)
    storage = ActivityStorage()

    for repo in args.repos:
        activity = tracker.track_repo(repo)
        if activity:
            storage.save_snapshot(activity)
            storage.add_tracked_repo(repo)
            print(f"Snapshot saved for {repo}")
        else:
            print(f"Failed to fetch data for {repo}")


def cmd_list(args: argparse.Namespace) -> None:
    """Handle the list command."""
    storage = ActivityStorage()
    repos = storage.get_tracked_repos()
    if repos:
        for repo in repos:
            print(repo)
    else:
        print("No repositories being tracked. Use 'track' command to add some.")


def cmd_trend(args: argparse.Namespace) -> None:
    """Handle the trend command."""
    storage = ActivityStorage()
    snapshots = storage.get_snapshots(args.repo, limit=args.days)
    if snapshots:
        print(f"Activity trend for {args.repo} (last {len(snapshots)} snapshots):")
        for snap in reversed(snapshots):
            print(f"  {snap['snapshot_at'][:10]} | stars={snap['stars']} | commits={snap['commits']}")
    else:
        print(f"No snapshot data for {args.repo}. Run 'snapshot' command first.")


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="gh-activity",
        description="GitHub Activity Tracker — monitor repo activity over time",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    track_parser = subparsers.add_parser("track", help="Track activity for repositories")
    track_parser.add_argument("repos", nargs="*", help="Repository names (owner/repo)")
    track_parser.add_argument("--input", "-i", help="Input file with repo names (one per line)")
    track_parser.add_argument("--days", "-d", type=int, default=30, help="Days of history (default: 30)")
    track_parser.add_argument("--format", "-f", choices=["text", "json", "csv"], default="text", help="Output format")
    track_parser.add_argument("--output", "-o", help="Output file")
    track_parser.add_argument("--token", "-t", help="GitHub token")
    track_parser.add_argument("--save", "-s", action="store_true", help="Save snapshots to database")
    track_parser.set_defaults(func=cmd_track)

    report_parser = subparsers.add_parser("report", help="Generate activity report")
    report_parser.add_argument("repo", help="Repository name (owner/repo)")
    report_parser.add_argument("--days", "-d", type=int, default=30, help="Days to analyze")
    report_parser.add_argument("--format", "-f", choices=["text", "json", "csv"], default="text")
    report_parser.add_argument("--output", "-o", help="Output file")
    report_parser.add_argument("--token", "-t", help="GitHub token")
    report_parser.set_defaults(func=cmd_report)

    snapshot_parser = subparsers.add_parser("snapshot", help="Save activity snapshot")
    snapshot_parser.add_argument("repos", nargs="*", help="Repository names")
    snapshot_parser.add_argument("--token", "-t", help="GitHub token")
    snapshot_parser.set_defaults(func=cmd_snapshot)

    list_parser = subparsers.add_parser("list", help="List tracked repositories")
    list_parser.set_defaults(func=cmd_list)

    trend_parser = subparsers.add_parser("trend", help="Show activity trends")
    trend_parser.add_argument("repo", help="Repository name")
    trend_parser.add_argument("--days", "-d", type=int, default=30, help="Number of snapshots")
    trend_parser.set_defaults(func=cmd_trend)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())