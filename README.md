# WatchGCG

This repo contains scripts to extract game data from GCG files in realtime for live stream broadcasts. Works as both a **CLI** tool and a **GUI** using the same script.

## Features

- **Automatic dependency handling**: The script auto-installs required modules (no need to pre-install).

- **Dual interface**: Run as CLI or GUI

- **Two output “versions”**:
   - ``std`` (default): one score file containing both players' scores
   - ``au``: separate score files for Player 1 and Player 2

## Requirements
- Python 3.7+ recommended (any modern Python 3 should work).

- ``watchfiles`` module is **installed automatically** on first run. If you prefer manual install:

    ```bash
    # Manual installation
    python -m pip install watchfiles
    # or
    python3 -m pip install watchfiles
    # on Windows if you use the launcher:
    py -m pip install watchfiles
    ```
> The script may optionally upgrade ``pip/setuptools/wheel``, but by default it does not (see ``ensure_awatch(upgrade_tools=False)`` in the code).

## Running the GUI
You have two options:
- UI (**Recommended**)
    - Double-click ``watch_gcg.py``
- CLI
    - Any **one** of these will open the GUI:

    ```bash
    python watch_gcg.py
    # OR
    python3 watch_gcg.py
    # OR
    py watch_gcg.py   # Windows launcher
    ```

>Running the GUI presumes that you have the TK App installed

## CLI Usage

### Default version -- one combined score file (``std``)

The script needs 6 arguments:

- The input GCG file to watch
- The input lexicon file with definitions
- The output file name for the scores
- The output file name for the unseen tiles
- The output file name for the unseen tiles count
- The output file name for the last play

For example, to watch a GCG file called 'test.gcg', use the following command:

```bash
python3 watch_gcg.py --gcg test.gcg --lex CSW24defs.csv --score score.txt --unseen unseentiles.txt --count unseencount.txt --lp lastplay.txt
```

### Australian version -- two score files (``--ver au``)

To output two separate score files, pass:
- ``--ver au``, and
- either one ``--score`` OR **both** ``--p1score`` and ``--p2score``

#### Option A (use ``--score`` only)

```bash
python3 watch_gcg.py --gcg test.gcg --lex CSW24defs.csv --ver au --score score.txt --unseen unseentiles.txt --count unseencount.txt --lp lastplay.txt
# writes ./p1_score.txt and ./p2_score.txt
```

#### Option B (use both ``--p1score`` and ``--p2score``)

```bash
python3 watch_gcg.py --gcg test.gcg --lex CSW24defs.csv --ver au --p1score p1_score.txt --p2score p2_score.txt --unseen unseentiles.txt --count unseencount.txt --lp lastplay.txt

```

## Notes
The script should now run indefinitely watching for changes to the GCG file. To stop execution in the terminal (CLI), hit ``Control-C``. In the GUI, close the window.

The output files update when you save the game. Editing/committing moves in Quackle without saving the ``.gcg`` file won’t trigger changes.
