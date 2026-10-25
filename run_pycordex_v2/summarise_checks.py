#!/usr/bin/env python3
"""
Summarise compliance-checker reports written by check_all_files.sh.

Writes, in the output folder:
  summary.txt              one file to read (or upload): every issue, its message,
                           and where it appears (frequency, variables, months)
  results.tsv              one line per file: file, exit code, seconds, report ok,
                           Required codes, other codes
  files_with_required.txt  Required codes and file, for every file with Required flags
  checker_errors.txt       files whose report is missing or broken

Usage:
  python3 summarise_checks.py <outdir> [root] [mode]
"""
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

LEVELS = {"Required": "Required", "Recommended": "Recommended",
          "Suggested": "Suggested", "Optional": "Suggested"}
CODE_RE = re.compile(r"^\[([A-Z]+[0-9]+)\]\s*(.*)$")
TOKEN_RE = re.compile(r"^(\d{6})\d*-\d+$")


def parse_report(path):
    """Return (ok, exit, seconds, [(level, code, title, message), ...])."""
    ok, ex, tm, items = False, "NA", "NA", []
    level = code = title = None
    with open(path, errors="replace") as f:
        for line in f:
            s = line.strip()
            if "IOOS Compliance Checker Report" in s:
                ok = True
            elif s in LEVELS:
                level, code = LEVELS[s], None
            elif s.startswith("#END"):
                for kv in s.split()[1:]:
                    k, _, v = kv.partition("=")
                    if k == "exit":
                        ex = v
                    elif k == "time":
                        tm = v
            elif level and CODE_RE.match(s):
                code, title = CODE_RE.match(s).groups()
                items.append([level, code, title, None])        # code without message yet
            elif level and code and s.startswith("* "):
                msg = s[2:]
                if items and items[-1][1] == code and items[-1][3] is None:
                    items[-1][3] = msg
                else:
                    items.append([level, code, title, msg])
    return ok, ex, tm, items


def month_ranges(months):
    """['197001', '197002', '197105'] -> '197001-197002, 197105'."""
    idx = sorted({int(m[:4]) * 12 + int(m[4:6]) - 1 for m in months})
    if not idx:
        return ""
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:] + [None]:
        if i is not None and i == prev + 1:
            prev = i
            continue
        runs.append((start, prev))
        if i is not None:
            start = prev = i
    fmt = lambda i: f"{i // 12:04d}{i % 12 + 1:02d}"
    txt = [fmt(a) if a == b else f"{fmt(a)}-{fmt(b)}" for a, b in runs]
    if len(txt) > 6:
        txt = txt[:3] + [f"... ({len(txt)} separate ranges) ..."] + txt[-2:]
    return ", ".join(txt) + f"  [{len(idx)} months]"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def names(affected, all_vars):
    affected, all_vars = sorted(affected), sorted(all_vars)
    if len(affected) == len(all_vars):
        return "all " + plural(len(all_vars), "variable")
    rest = sorted(set(all_vars) - set(affected))
    if len(affected) <= 12:
        return f"{len(affected)} of {len(all_vars)} variables: {', '.join(affected)}"
    if len(rest) <= 12:
        return f"{len(affected)} of {len(all_vars)} variables, all except: {', '.join(rest)}"
    return f"{len(affected)} of {len(all_vars)} variables, e.g. {', '.join(affected[:8])}, ..."


def main():
    outdir = sys.argv[1].rstrip("/")
    root = sys.argv[2] if len(sys.argv) > 2 else ""
    mode = sys.argv[3] if len(sys.argv) > 3 else ""
    repdir = os.path.join(outdir, "reports")

    files_listed = 0
    if os.path.exists(os.path.join(outdir, "files.txt")):
        with open(os.path.join(outdir, "files.txt")) as f:
            files_listed = sum(1 for _ in f)

    rows, errors = [], []
    vars_by_freq = defaultdict(set)
    time_by_freq = defaultdict(list)
    issues = {}   # (level, code, normalised message) -> details
    code_files = defaultdict(set)   # (level, code) -> files

    for d, _, fnames in os.walk(repdir):
        for fn in fnames:
            if not fn.endswith(".txt"):
                continue
            rel = os.path.relpath(os.path.join(d, fn), repdir)[:-4] + ".nc"
            parts = rel.split(os.sep)
            freq, var = (parts[0], parts[1]) if len(parts) >= 3 else ("?", "?")
            m = TOKEN_RE.match(os.path.basename(rel)[:-3].split("_")[-1])
            month = m.group(1) if m else None
            ok, ex, tm, items = parse_report(os.path.join(d, fn))
            vars_by_freq[freq].add(var)
            if tm != "NA":
                time_by_freq[freq].append(float(tm))
            if not ok:
                errors.append(rel)
            req = sorted({c for lv, c, _, _ in items if lv == "Required"})
            oth = sorted({c for lv, c, _, _ in items if lv != "Required"})
            rows.append((rel, ex, tm, int(ok), ",".join(req) or "-", ",".join(oth) or "-"))
            for lv, code, title, msg in items:
                msg = msg or "(no message)"
                key = (lv, code, re.sub(r"\d+", "#", msg))
                it = issues.setdefault(key, {"title": title, "example": msg, "file": rel,
                                             "files": 0, "where": defaultdict(lambda: defaultdict(list))})
                it["files"] += 1
                code_files[(lv, code)].add(rel)
                it["where"][freq][var].append(month)

    rows.sort()
    with open(os.path.join(outdir, "results.tsv"), "w") as f:
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    with open(os.path.join(outdir, "files_with_required.txt"), "w") as f:
        for r in rows:
            if r[4] != "-":
                f.write(f"{r[4]}\t{r[0]}\n")
    with open(os.path.join(outdir, "checker_errors.txt"), "w") as f:
        f.write("".join(e + "\n" for e in sorted(errors)))

    n_req = sum(1 for r in rows if r[4] != "-")
    order = {"Required": 0, "Recommended": 1, "Suggested": 2}
    out = []
    w = out.append
    w(f"Compliance check summary ({mode}), {datetime.now():%Y-%m-%d %H:%M}")
    if root:
        w(f"Root: {root}")
    w("")
    w(f"Files in list:              {files_listed}")
    w(f"Reports found:              {len(rows)}")
    w(f"Checker errors / no report: {len(errors)}   (checker_errors.txt)")
    w(f"Files with Required flags:  {n_req}   (files_with_required.txt)")
    w(f"Files with no Required flag: {len(rows) - n_req}")
    w("")
    w("Files checked per frequency: " + ", ".join(
        f"{fq} {sum(1 for r in rows if r[0].split(os.sep)[0] == fq)}" for fq in sorted(vars_by_freq)))
    w("")

    # overview table
    w("Overview (level, code, number of files):")
    for (lv, code), fs in sorted(code_files.items(), key=lambda x: (order[x[0][0]], x[0][1])):
        w(f"  {lv:<12} {code:<9} {len(fs)}")
    w("")

    # details
    w("=" * 78)
    w("Issues and where they appear")
    w("=" * 78)
    for (lv, code, _), it in sorted(issues.items(), key=lambda x: (order[x[0][0]], x[0][1], -x[1]["files"])):
        w("")
        w(f"[{lv}] {code} {it['title']}   ({it['files']} files)")
        w(f"  Message:  {it['example']}")
        w(f"  Example:  {it['file']}")
        for fq in sorted(it["where"]):
            vmap = it["where"][fq]
            nfiles = sum(len(v) for v in vmap.values())
            w(f"  {fq}: {nfiles} files; {names(vmap.keys(), vars_by_freq[fq])}")
            months = [mo for v in vmap.values() for mo in v if mo]
            if months:
                w(f"        months: {month_ranges(months)}")

    w("")
    w("Mean check time per file:")
    for fq in sorted(time_by_freq):
        t = time_by_freq[fq]
        w(f"  {fq:<5} {sum(t) / len(t):5.1f} s  ({len(t)} files)")

    if mode == "sample" and root and time_by_freq:
        nproc = int(os.environ.get("NPROC_USED", "112"))
        total_s = total_n = 0
        for fq in time_by_freq:
            n = sum(len([x for x in fs if x.endswith(".nc")])
                    for _, _, fs in os.walk(os.path.join(root, fq)))
            total_s += n * sum(time_by_freq[fq]) / len(time_by_freq[fq])
            total_n += n
        w("")
        w(f"Estimated wall time for 'all' with {nproc} in parallel: "
          f"{total_n} files, about {total_s / nproc / 3600:.1f} h")

    with open(os.path.join(outdir, "summary.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
