# WatchGCG

This repo contains scripts to extract game data from GCG files in realtime for live stream broadcasts. Works as both a **GUI** and a **CLI** tool using the same script.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Running the GUI](#running-the-gui)
- [CLI Usage](#cli-usage)
   - [Default Version](#default-version----one-combined-score-file-std)
   - [Australian Version](#australian-version----two-score-files---ver-au)
- [Notes](#notes)

## Features

- **Automatic Dependency Handling**: The script auto-installs required modules (no need to pre-install anything).

- **Dual Interface**: The same script can be run as a graphical interface (GUI) or from the command line (CLI).

- **Version Selection**: Supports both the default (``std``) and Australian (``au``) versions of the script (choose with the optional ``--ver`` parameter).

   - ``std``: outputs one score file containing both players' scores
   - ``au``: outputs separate score files for Player 1 and Player 2

## Requirements
- Python 3.7+ recommended (any modern Python 3 should work).

- ``watchfiles`` module is **installed automatically** on first run. If you prefer manual install instead, run:

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
>Running the GUI presumes that you have the TK App installed (Windows & the official macOS python.org installers already include Tk.)

You have two options:
- UI (**Recommended**)
    - Clone the repo or download the ``watch_gcg.py`` script to your computer
    - Double-click ``watch_gcg.py``
- CLI
    - Clone the repo or download the ``watch_gcg.py`` script to your computer
    - Navigate to its directory in the Command Terminal
    - Any **one** of these will open the GUI:

    ```bash
    python watch_gcg.py
    # OR
    python3 watch_gcg.py
    # OR
    py watch_gcg.py   # Windows launcher
    ```



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
