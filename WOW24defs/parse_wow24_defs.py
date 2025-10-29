import re
import argparse
from pathlib import Path

VALID_POS = {'n', 'v', 'adj', 'adv', 'interj', 'pron', 'prep', 'conj'}

# --- Parsers ---------------------------------------------------------------

def split_root_head_and_tail(line: str):
    """
    For a root line (e.g. 'AAH to exclaim ... [v -ED, -ING, -S]'),
    return (headword, tail_full).
    tail_full is everything after the headword, including any '(...)', ', also ...',
    and the bracketed POS/conjugations.
    """
    m = re.match(r'^([A-Z]+)\b(.*)$', line.strip())
    if not m:
        return None, None
    return m.group(1), m.group(2).strip()

def tail_up_to_bracket(tail_full: str):
    """
    Return everything before the first '[' (not including it), trimmed.
    This preserves (language of origin) and ', also ...' exactly.
    """
    i = tail_full.find('[')
    if i == -1:
        # If no '[', keep the whole tail
        return tail_full.strip()
    return tail_full[:i].strip()

def parse_nonroot_line(line: str):
    """
    Non-root lines look like: 'ABORIGINALITY <aboriginal=n> [n -TIES]'
    Return (derived_upper, root_upper, derived_pos) or None if not matched.
    """
    s = line.strip()
    # Case 1: <root=pos>
    m = re.match(r'^([A-Z]+)\s*<([A-Za-z]+)\s*=\s*([a-zA-Z]+)>\s*\[([^\]]+)\](?:.*)?$', s)
    if m:
        derived_upper = m.group(1)
        parent_upper  = m.group(2).upper()
        pos = m.group(3).lower()
        bracket_inner = m.group(4).strip()
        return derived_upper, parent_upper, bracket_inner

    # Case 2: <root> (no =pos)
    m = re.match(r'^([A-Z]+)\s*<([A-Za-z]+)>\s*\[([^\]]+)\](?:.*)?$', s)
    if m:
        derived_upper = m.group(1)
        parent_upper  = m.group(2).upper()
        bracket_inner = m.group(3).strip()
        return derived_upper, parent_upper, bracket_inner

    return None


def is_nonroot_format(line: str) -> bool:
    """
    Non-root lines look like:
        WORD <root=pos> [pos]
    i.e., after the ALL-CAPS headword and optional spaces, the very next
    character is '<'.
    """
    return bool(re.match(r'^[A-Z]+\s*<', line.strip()))

def is_root_format(line: str) -> bool:
    """
    Root lines start with an ALL-CAPS headword and do NOT have '<' immediately
    after the headword. They also contain a '[' later for POS/conjugations.
    """
    s = line.strip()
    return bool(re.match(r'^[A-Z]+\b(?!\s*<)', s)) and '[' in s



# ---------- resolver for nested chains ----------
def build_maps(lines):
    root_tail_prefix = {}   # ROOT -> text before '['
    nonroot_parent  = {}    # NONROOT -> parent headword
    nonroot_bracket = {}    # NONROOT -> full bracket text (e.g., 'n -TIES')
    malformed_roots  = []
    misc_lines       = []

    for line in lines:
        if not line.strip():
            continue
        if is_root_format(line):
            root, tail_full = split_root_head_and_tail(line)
            if root:
                root_tail_prefix[root] = tail_up_to_bracket(tail_full)
        elif re.match(r'^[A-Z]+\b', line.strip()) and '[' not in line:
            # Looks like a root (all caps start) but missing '[', mark as malformed
            malformed_roots.append(line.strip())
        
        elif is_nonroot_format(line):
            parsed = parse_nonroot_line(line)
            if parsed:
                child, parent, bracket_inner = parsed
                nonroot_parent[child] = parent
                nonroot_bracket[child] = bracket_inner

        else:
            misc_lines.append(line.strip())

    return root_tail_prefix, nonroot_parent, nonroot_bracket, malformed_roots, misc_lines

    

def resolve_ultimate_root(headword_upper, root_tail_prefix, nonroot_parent):
    seen = set()
    current = headword_upper
    while current not in root_tail_prefix:
        if current in seen:
            raise ValueError(f"Cycle while resolving root for {headword_upper}: {' -> '.join(seen)}")
        seen.add(current)
        parent = nonroot_parent.get(current)
        if parent is None:
            raise KeyError(f"No ultimate root found for {headword_upper}; stopped at {current}")
        current = parent
    return current

# --- Main ------------------------------------------------------------------

def update_defs(input_path: str, output_path: str):
    """
    Output txt file with:

    - ROOT lines (untouched): ROOT<TAB><original tail (everything after headword)>
    - NON-ROOT lines (updated): WORD<TAB>ROOT, <root tail up to '['> [<derived POS>]
    """
    lines = Path(input_path).read_text(encoding='utf-8').splitlines()
    root_tail_prefix, nonroot_parent, nonroot_bracket, malformed_roots, misc_lines = build_maps(lines)

    out = []
    errors = []

    for line in lines:
        if not line.strip():
            continue

        if is_root_format(line):
            root, tail_full = split_root_head_and_tail(line)
            if root:
                out.append(f"{root}\t{tail_full}")
            else:
                out.append(line)
                errors.append(f"Malformed root line: {line}")

        elif is_nonroot_format(line):
            parsed = parse_nonroot_line(line)
            if not parsed:
                out.append(line)
                errors.append(f"Unparseable non-root line: {line}")
                continue

            derived, parent, bracket_inner = parsed

            try:
                ultimate = resolve_ultimate_root(parent, root_tail_prefix, nonroot_parent)
                prefix = root_tail_prefix[ultimate]
                out.append(f"{derived}\t{ultimate}, {prefix} [{bracket_inner}]")
            except Exception as e:
                out.append(line)
                # Instead of raising, log the error
                errors.append(f"Resolution error for {derived}: {line} | Error={e}")
        else:
            out.append(line)
            errors.append(f"Misc line: {line}")

            
    Path(output_path).write_text("\n".join(out) + "\n", encoding='utf-8')

    errors_path = Path(output_path).with_name("WOW24_errors.txt")
    Path(errors_path).write_text("\n".join(errors) + "\n", encoding='utf-8')

    # Report problems
    print(f"Done. Output written to {output_path}")
    print(f"{len(errors)} issues written to {errors_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process dictionary file into combined output.")
    parser.add_argument("input", nargs="?", default="./WOW24defs.txt",
                        help="Path to input .txt file (default: WOW24defs.txt)")
    parser.add_argument("output", nargs="?", default="WOW24_updated.txt",
                        help="Path to output .txt file (default: WOW24_updated.txt)")
    args = parser.parse_args()

    update_defs(args.input, args.output)


update_defs("WOW24defs.txt", "WOW24_updated.txt")

# Example usage:
# write_all_definitions_tsv("lexicon.txt", "all_definitions.txt")

