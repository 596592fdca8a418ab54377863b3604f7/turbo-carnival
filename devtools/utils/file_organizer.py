#!/usr/bin/env python3
"""
File Organizer - Search, organize, and manage files from the terminal
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import mimetypes

try:
    from utils.security import (
        SecurityError,
        assert_readable_directory,
        assert_safe_write_path,
        parse_positive_int,
        resolve_path,
    )
except ImportError:
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
    from utils.security import (
        SecurityError,
        assert_readable_directory,
        assert_safe_write_path,
        parse_positive_int,
        resolve_path,
    )


class FileOrganizer:
    """Organize and manage files"""

    SKIP_DIRS = {'.git', '.hg', '.svn', '__pycache__', 'node_modules', '.venv', 'venv'}

    def __init__(self, directory: str):
        self.directory = resolve_path(directory)
        self.files: List[Path] = []

    def scan_directory(self, recursive: bool = True) -> List[Path]:
        """Scan directory for files (skips symlinks and VCS trees)"""
        assert_readable_directory(self.directory)
        base = self.directory.resolve(strict=False)

        candidates = self.directory.rglob('*') if recursive else self.directory.glob('*')
        files = []
        for f in candidates:
            if any(part in self.SKIP_DIRS for part in f.parts):
                continue
            if f.is_symlink():
                continue
            if not f.is_file():
                continue
            try:
                f.resolve(strict=False).relative_to(base)
            except (ValueError, OSError):
                continue
            files.append(f)

        self.files = files
        print(f"✓ Found {len(self.files)} files in {self.directory}")
        return self.files

    def search_by_name(self, pattern: str, case_sensitive: bool = False) -> List[Path]:
        """Search files by name pattern (literal substring, not regex)"""
        if not case_sensitive:
            needle = pattern.lower()
            results = [f for f in self.files if needle in f.name.lower()]
        else:
            results = [f for f in self.files if pattern in f.name]

        print(f"✓ Found {len(results)} files matching '{pattern}'")
        return results

    def search_by_extension(self, extension: str) -> List[Path]:
        """Search files by extension"""
        if not extension.startswith('.'):
            extension = '.' + extension
        results = [f for f in self.files if f.suffix.lower() == extension.lower()]
        print(f"✓ Found {len(results)} files with extension '{extension}'")
        return results

    def search_by_size(self, min_size: int = None, max_size: int = None) -> List[Path]:
        """Search files by size (in bytes)"""
        results = []
        for f in self.files:
            try:
                size = f.stat().st_size
            except OSError:
                continue
            if min_size is not None and size < min_size:
                continue
            if max_size is not None and size > max_size:
                continue
            results.append(f)

        print(f"✓ Found {len(results)} files matching size criteria")
        return results

    def search_by_date(self, days: int = None) -> List[Path]:
        """Search files modified in last N days"""
        if days is None:
            return self.files

        cutoff = datetime.now().timestamp() - (days * 86400)
        results = []
        for f in self.files:
            try:
                if f.stat().st_mtime > cutoff:
                    results.append(f)
            except OSError:
                continue
        print(f"✓ Found {len(results)} files modified in last {days} days")
        return results

    def get_file_info(self, file_path: Path) -> Dict:
        """Get detailed information about a file"""
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            'name': file_path.name,
            'path': str(file_path),
            'size': stat.st_size,
            'size_human': self._human_readable_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'extension': file_path.suffix,
            'mime_type': mime_type or 'unknown'
        }

    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def print_results(self, files: List[Path], limit: int = 20):
        """Print search results"""
        if not files:
            print("No files found")
            return

        print(f"\nResults ({len(files)} files):")
        print("-" * 80)
        print(f"{'Name':<40} {'Size':>12} {'Modified':>20}")
        print("-" * 80)

        for file_path in files[:limit]:
            try:
                info = self.get_file_info(file_path)
            except OSError:
                continue
            print(f"{info['name']:<40} {info['size_human']:>12} {info['modified']:>20}")

        if len(files) > limit:
            print(f"... and {len(files) - limit} more files")

    def organize_by_extension(self, target_dir: str = None, dry_run: bool = True):
        """Organize files into folders by extension"""
        if target_dir is None:
            target_path = self.directory / "organized"
        else:
            target_path = resolve_path(target_dir)

        if not dry_run:
            try:
                parent = target_path if target_path.exists() else target_path.parent
                if not parent.exists():
                    raise SecurityError(f"Target parent does not exist: {parent}")
                assert_safe_write_path(parent / ".devtools_perm_probe")
                if target_path.exists() and not target_path.is_dir():
                    raise SecurityError(f"Organize target is not a directory: {target_path}")
            except SecurityError as e:
                print(f"✗ Security: {e}")
                return

        extension_counts = {}
        skipped = 0

        for file_path in self.files:
            # Never move files that are already under the target tree
            try:
                file_path.resolve(strict=False).relative_to(target_path.resolve(strict=False))
                continue
            except ValueError:
                pass

            ext = file_path.suffix.lower()
            if not ext:
                folder_name = 'no_extension'
            else:
                folder_name = ext[1:]  # Remove the leading dot

            if dry_run:
                extension_counts[folder_name] = extension_counts.get(folder_name, 0) + 1
            else:
                ext_dir = target_path / folder_name
                try:
                    ext_dir.mkdir(parents=True, exist_ok=True)
                    dest = ext_dir / file_path.name
                    if dest.exists():
                        print(f"⚠ Skip (destination exists): {dest}")
                        skipped += 1
                        continue
                    shutil.move(str(file_path), str(dest))
                except OSError as e:
                    print(f"✗ Failed to move {file_path}: {e}")
                    skipped += 1

        if dry_run:
            print("\nDry run - would organize files into:")
            for folder, count in sorted(extension_counts.items()):
                print(f"  {folder}/: {count} files")
        else:
            print(f"✓ Organized files into {target_path}"
                  + (f" ({skipped} skipped)" if skipped else ""))

    def find_duplicates(self) -> Dict[str, List[Path]]:
        """Find duplicate files by name"""
        name_map: Dict[str, List[Path]] = {}
        for file_path in self.files:
            name_map.setdefault(file_path.name, []).append(file_path)

        duplicates = {name: paths for name, paths in name_map.items() if len(paths) > 1}

        if duplicates:
            print(f"✓ Found {len(duplicates)} sets of duplicate files")
            for name, paths in duplicates.items():
                print(f"  {name}: {len(paths)} copies")
        else:
            print("✓ No duplicate files found")

        return duplicates

    def clean_empty_dirs(self, dry_run: bool = True):
        """Find and remove empty directories (deepest first)"""
        empty_dirs = []
        for dir_path in sorted(self.directory.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if any(part in self.SKIP_DIRS for part in dir_path.parts):
                continue
            if dir_path.is_symlink() or not dir_path.is_dir():
                continue
            try:
                if not any(dir_path.iterdir()):
                    empty_dirs.append(dir_path)
            except OSError:
                continue

        if empty_dirs:
            print(f"✓ Found {len(empty_dirs)} empty directories")
            if dry_run:
                for dir_path in empty_dirs[:20]:
                    print(f"  would remove: {dir_path}")
                if len(empty_dirs) > 20:
                    print(f"  ... and {len(empty_dirs) - 20} more")
            else:
                removed = 0
                for dir_path in empty_dirs:
                    try:
                        dir_path.rmdir()
                        removed += 1
                    except OSError as e:
                        print(f"✗ Failed to remove {dir_path}: {e}")
                print(f"✓ Removed {removed} empty directories")
        else:
            print("✓ No empty directories found")


def main():
    """Main entry point for file organizer"""
    if len(sys.argv) < 2:
        print("Usage: python file_organizer.py <directory> [options]")
        print("\nOptions:")
        print("  --name <pattern>          Search by name pattern")
        print("  --ext <extension>         Search by extension")
        print("  --size <min> <max>        Search by size range (bytes)")
        print("  --days <N>                Search files modified in last N days")
        print("  --organize <dir>          Organize files by extension")
        print("  --duplicates              Find duplicate files")
        print("  --clean-empty             Find empty directories")
        print("  --execute                 Execute operations (not dry run)")
        print("  --limit <N>               Limit results display")
        sys.exit(1)

    directory = sys.argv[1]
    if directory.startswith('-'):
        print("✗ Error: Please specify a directory before options")
        sys.exit(1)

    try:
        organizer = FileOrganizer(directory)
        organizer.scan_directory()
    except SecurityError as e:
        print(f"✗ Security: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

    try:
        limit = 20
        if '--limit' in sys.argv:
            limit_idx = sys.argv.index('--limit') + 1
            if limit_idx < len(sys.argv):
                limit = parse_positive_int(sys.argv[limit_idx], name='--limit', allow_zero=False)

        if '--name' in sys.argv:
            name_idx = sys.argv.index('--name') + 1
            if name_idx < len(sys.argv):
                results = organizer.search_by_name(sys.argv[name_idx])
                organizer.print_results(results, limit)

        if '--ext' in sys.argv:
            ext_idx = sys.argv.index('--ext') + 1
            if ext_idx < len(sys.argv):
                results = organizer.search_by_extension(sys.argv[ext_idx])
                organizer.print_results(results, limit)

        if '--size' in sys.argv:
            size_idx = sys.argv.index('--size') + 1
            min_size = None
            max_size = None
            if size_idx < len(sys.argv) and not sys.argv[size_idx].startswith('-'):
                min_size = parse_positive_int(sys.argv[size_idx], name='--size min')
            if size_idx + 1 < len(sys.argv) and not sys.argv[size_idx + 1].startswith('-'):
                max_size = parse_positive_int(sys.argv[size_idx + 1], name='--size max')
            results = organizer.search_by_size(min_size, max_size)
            organizer.print_results(results, limit)

        if '--days' in sys.argv:
            days_idx = sys.argv.index('--days') + 1
            if days_idx < len(sys.argv):
                days = parse_positive_int(sys.argv[days_idx], name='--days', allow_zero=False)
                results = organizer.search_by_date(days)
                organizer.print_results(results, limit)

        if '--organize' in sys.argv:
            org_idx = sys.argv.index('--organize') + 1
            target_dir = (
                sys.argv[org_idx]
                if org_idx < len(sys.argv) and not sys.argv[org_idx].startswith('-')
                else None
            )
            dry_run = '--execute' not in sys.argv
            if not dry_run:
                print("⚠ --execute will move files. Continuing...")
            organizer.organize_by_extension(target_dir, dry_run)

        if '--duplicates' in sys.argv:
            organizer.find_duplicates()

        if '--clean-empty' in sys.argv:
            dry_run = '--execute' not in sys.argv
            if not dry_run:
                print("⚠ --execute will delete empty directories. Continuing...")
            organizer.clean_empty_dirs(dry_run)

    except SecurityError as e:
        print(f"✗ Security: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
