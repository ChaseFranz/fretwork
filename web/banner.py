"""
BANNER - the terminal output around serve_forever and after publish
"""

import pathlib

from web.bootstrap import BOOTSTRAP_VERSION


def print_startup(xlsx_path, frames, total, bootstrap_css, port, packs_line=None):
    style = (f"Bootstrap {BOOTSTRAP_VERSION} (served locally)"
             if bootstrap_css else "built-in fallback")
    print(f"\nServing {xlsx_path}")
    print(f"    {total} rows across {len(frames)} sheet(s): {', '.join(frames)}")
    print(f"    styles: {style}")
    if packs_line:
        print("    " + packs_line.replace("\n", "\n    "))
    print(f"\n    http://localhost:{port}\n")
    print("Ctrl+C to stop\n")


def print_stopped():
    print("\nStopped\n")


def print_published(out_dir, page_files, written, removed, counts, graph_files, packs_line=None):
    out = pathlib.Path(out_dir)
    paths = [out / name for name in page_files + graph_files]
    size_mb = sum(q.stat().st_size for q in paths if q.is_file()) / 1_048_576
    c = counts
    print(f"\nPublished to {out_dir}/")
    if packs_line:
        print(f"    {packs_line}")
    print(f"    page files: {written} written, {len(page_files) - written} unchanged"
          + (f", {removed} removed" if removed else ""))
    print(f"    graphs: {c['rendered']} rendered, {c['unchanged']} unchanged, {c['kept']} kept "
          f"from before, {c['no_graph']} without a graph, {c['failed']} failed, {c['pruned']} pruned")
    print(f"    {len(paths)} files, {size_mb:.1f} MB\n")
