import argparse
from pathlib import Path

# ---------- Helpers ----------

def load_defs(path):
    """
    Load a defs file: UPPERCASE_WORD<TAB>definition
    Returns dict: {WORD: definition}
    Ignores blank lines; keeps definitions exactly as-is.
    """
    d = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if "\t" not in line:
                # If a malformed row appears, skip it silently
                continue
            word, definition = line.split("\t", 1)
            word = word.strip().upper()
            d[word] = definition.strip()
    return d

def load_wordlist(path):
    """
    Load a plain word list file with one UPPERCASE word per line.
    Returns a set of WORDs.
    """
    s = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().upper()
            if w:
                s.add(w)
    return s

def write_csv(path, rows):
    """
    Write rows of (word_with_tags, definition or '') as CSV:
    WORD,'definition'
    Ensures single quotes around definition (even if empty).
    """
    with open(path, "w", encoding="utf-8", newline="") as out:
        for w, d in rows:
            d = "" if d is None else d
            out.write(f"{w},'{d}'\n")

def append_marker(base, marker):
    """
    Append a marker (one of '#', '+', '$', 'x') exactly once.
    If the word already ends with that marker, do nothing.
    """
    return base if base.endswith(marker) else (base + marker)

def report_missing(stage, words, defs_map, limit=5):
    missing = [w for w in sorted(words) if defs_map.get(w, "") == ""]
    cnt = len(missing)
    preview = ", ".join(missing[:limit])
    print(f"[DEBUG] {stage}: missing definitions = {cnt}")
    if cnt:
        print(f"[DEBUG] {stage}: first {min(limit, cnt)} missing -> {preview}")
    return cnt

# ---------- Core pipeline ----------

def main(args):
    # Inputs
    nwl23_defs = load_defs(args.nwl23_defs)
    csw24_defs = load_defs(args.csw24_defs)
    csw21_defs = load_defs(args.csw21_defs)
    nwl18_defs = load_defs(args.nwl18_defs)
    nwl20_defs = load_defs(args.nwl20_defs)
    wow24_words = load_wordlist(args.wow24_words)

    # Base sets (raw words, untagged)
    set_nwl18 = set(nwl18_defs.keys())
    set_nwl20 = set(nwl20_defs.keys())
    set_nwl23 = set(nwl23_defs.keys())
    set_csw24 = set(csw24_defs.keys())
    set_csw21 = set(csw21_defs.keys())
    set_wow24 = set(wow24_words)

    # ---------- WOW24: staged definition fill (NWL18 -> NWL20 -> NWL23) ----------
    # Start with NWL18
    wow24_defs = {w: nwl18_defs.get(w, "") for w in set_wow24}

    # Fill from NWL20 where still missing, then report
    for w in set_wow24:
        if wow24_defs[w] == "" and w in nwl20_defs:
            wow24_defs[w] = nwl20_defs[w]
    report_missing("After NWL20 fill", set_wow24, wow24_defs)

    # If still missing, fill from NWL23, then report
    any_missing = any(wow24_defs[w] == "" for w in set_wow24)
    if any_missing:
        for w in set_wow24:
            if wow24_defs[w] == "" and w in nwl23_defs:
                wow24_defs[w] = nwl23_defs[w]
        report_missing("After NWL23 fill", set_wow24, wow24_defs)

    # Build WOW24 rows
    wow24_rows = []
   
   # plus_words = []
    for w in sorted(set_wow24):
        display = w
        # in WOW24 but not in NWL23 AND not in CSW24 -> 'x'
        if (w not in set_nwl23) and (w not in set_csw24):
            display = append_marker(display, "x")
        
        # in WOW24 but not in NWL20 AND not in NWL18 -> '+'
        if (w not in set_nwl20) and (w not in set_nwl18):
            display = append_marker(display, "+")
            # plus_words.append(w)

        wow24_rows.append((display, wow24_defs[w]))
    
   # Debuggng: track WOW24 words that get '+'
    
   # print(f"[DEBUG] WOW24 words with '+': {len(plus_words)}")
   # if plus_words:
   #     print("[DEBUG] First 5 WOW24 words with '+':", ", ".join(plus_words[:5]))

    # ---------- Build CSW24 (apply # and +) ----------
    csw24_rows = []
    for w in sorted(set_csw24):
        display = w

        # in CSW24 but not in NWL23 AND not in WOW24 -> '#'
        if (w not in set_nwl23) and (w not in set_wow24):
            display = append_marker(display, "#")

        # in CSW24 but not in CSW21 -> '+'
        if w not in set_csw21:
            display = append_marker(display, "+")

        definition = csw24_defs[w]
        csw24_rows.append((display, definition))

    # ---------- Build NWL23 (apply $ and x) ----------
    nwl23_rows = []
    for w in sorted(set_nwl23):
        display = w

        # in NWL23 but not in CSW24 -> '$'
        if w not in set_csw24:
            display = append_marker(display, "$")

        # in NWL23 but not in WOW24 -> 'x'
        if w not in set_wow24:
            display = append_marker(display, "x")

        # in NWL23 but not in NWL20 -> '+'
        if w not in set_nwl20:
            display = append_marker(display, "+")

        definition = nwl23_defs[w]
        nwl23_rows.append((display, definition))

    # ---------- Write CSV outputs ----------
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(out_dir / "NWL23_lexsym.csv", nwl23_rows)
    write_csv(out_dir / "CSW24_lexsym.csv", csw24_rows)
    write_csv(out_dir / "WOW24_lexsym.csv", wow24_rows)

    print("Done.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Create tagged CSVs for NWL23, CSW24, WOW24 with staged def fill (NWL18 -> NWL20 -> NWL23) and symbol rules.")
    p.add_argument("--nwl23-defs", required=True, help="Path to nwl23_defs.txt (WORD<TAB>definition)")
    p.add_argument("--csw24-defs", required=True, help="Path to csw24_defs.txt (WORD<TAB>definition)")
    p.add_argument("--csw21-defs", required=True, help="Path to csw21_defs.txt (WORD<TAB>definition)")
    p.add_argument("--nwl18-defs", required=True, help="Path to nwl18_defs.txt (WORD<TAB>definition)")
    p.add_argument("--nwl20-defs", required=True, help="Path to nwl20_defs.txt (WORD<TAB>definition)")
    p.add_argument("--wow24-words", required=True, help="Path to WOW24.txt (one WORD per line)")
    p.add_argument("--output-dir", default=".", help="Directory to write NWL23.csv, CSW24.csv, WOW24.csv")
    args = p.parse_args()
    main(args)
