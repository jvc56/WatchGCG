#!/usr/bin/env python3

AUTOSIM_DEBUG = False

def _magpie_debug(*args, **kwargs):
    if AUTOSIM_DEBUG:
        print(*args, **kwargs)

import os
import re
import sys
from pathlib import Path
import argparse
import asyncio
import subprocess

#-----------------------------
# Install watchfiles if missing
#-----------------------------

def ensure_requirements():
    here = Path(__file__).resolve().parent
    req = here / "requirements.txt"

    if not req.exists():
        return  # nothing to install

    try:
        # Fast path: assume requirements already installed
        import watchfiles
        return
    except ModuleNotFoundError:
        pass

    print("Installing requirements from requirements.txt…", file=sys.stderr)

    cmd = [
        sys.executable,
        "-m", "pip",
        "install",
        "-r", str(req),
    ]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print(
            "\nERROR: Failed to install requirements.\n"
            "Try running:\n"
            f"  {sys.executable} -m pip install -r {req}\n",
            file=sys.stderr
        )
        sys.exit(1)

    import importlib
    importlib.invalidate_caches()

# The Pillow library is not a strict requirement as it is only needed
# to produce board images.

_PIL_INSTALLED = False

def ensure_pil(log_fn=None):
    """
    Ensure Pillow (PIL) is available and functional. 
    Throws RuntimeError if installation or import fails.
    """
    global _PIL_INSTALLED
    if _PIL_INSTALLED:
        return True

    def _log(msg):
        if log_fn: log_fn(msg + "\n")
        else: print(msg, file=sys.stderr)

    try:
        from PIL import Image
        # Test that the compiled extension works
        Image.new('RGB', (1, 1)) 
        _PIL_INSTALLED = True
        return True
    except (ImportError, AttributeError):
        # This catches the '_imaging' import error specifically
        pass

    py = sys.executable or "python"
    _log("Pillow installation is missing or broken. Attempting fix/install...")
    
    try:
        cmd = [py, "-m", "pip", "install", "--force-reinstall", "Pillow"]
        if getattr(sys, "base_prefix", sys.prefix) == sys.prefix:
            cmd += ["--user"]
        subprocess.check_call(cmd)
        
        # Final verification
        from PIL import Image
        Image.new('RGB', (1, 1))
        _PIL_INSTALLED = True
        return True
    except Exception as e:
        raise RuntimeError(
            "Failed to install or repair 'Pillow'. Image generation cannot proceed.\n"
            f"Error: {e}\n"
            f"Try running: {py} -m pip install --force-reinstall Pillow"
        )

#----------------------------
# Main logic
#----------------------------

vowels = "aeiouAEIOU"

LEX_SUFFIX_RE = re.compile(r'[+#x$]+$')

def _clean_csv_key(s: str) -> str:
    return LEX_SUFFIX_RE.sub('', s.strip()).upper()

BOARD_SIZE = 15

MOVE_TYPE_UNSPECIFIED = 0
MOVE_TYPE_TILE_PLACEMENT = 1
MOVE_TYPE_EXCHANGE = 2
MOVE_TYPE_PASS = 3

LAST_PLAY_PREFIX = "     LAST PLAY: "
POWER_TILES_SET = set('SJQXZ?')


class Players:
    def __init__(self):
        self.names = ["", ""]
        self.scores = [0, 0]
        self.names_to_indexes = {}

    def get_index(self, name_or_index):
        if isinstance(name_or_index, int):
            if name_or_index < 0 or name_or_index > 1:
                raise ValueError(f'Player index out of range: {name_or_index}')
            return name_or_index
        elif isinstance(name_or_index, str):
            if name_or_index in self.names_to_indexes:
                return self.names_to_indexes[name_or_index]
            else:
                raise ValueError(f'Could not find index for player: {name_or_index}')
        else:
            raise ValueError(f'Cannot index players with {name_or_index}')

    def get_name(self, index):
        return self.names[index]

    def set_name(self, index, name):
        self.names[index] = name
        self.names_to_indexes[name] = index
    
    def get_score(self, name_or_index):
        return self.scores[self.get_index(name_or_index)]

    def set_score(self, name_or_index, score):
        self.scores[self.get_index(name_or_index)] = int(score)

def get_unique_image(char_to_load):
    directory = 'img/'
    
    files = os.listdir(directory)
    
    matches = [f for f in files if os.path.splitext(f)[0] == char_to_load]
    
    if len(matches) == 0:
        raise FileNotFoundError(f"Error: No file named '{char_to_load}' found in {directory}")
    elif len(matches) > 1:
        raise RuntimeError(f"Error: Multiple extensions found for '{char_to_load}': {matches}")
    
    return os.path.join(directory, matches[0])

class Board:
    def __init__(self):
        self.matrix = [['' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

    def get_row_and_col_from_position(self, position):
        if position[0].isdigit():
            # Horizontal play
            row_end_index = 1
            if position[1].isdigit():
                row_end_index = 2
            row = int(position[:row_end_index]) - 1
            col = ord(position[row_end_index:]) - ord('A')
        else:
            # Vertical play
            col = ord(position[0]) - ord('A')
            row = int(position[1:]) - 1
        return row, col

    def place_tiles(self, position, word):
        row, col = self.get_row_and_col_from_position(position)
        for i, tile in enumerate(word):
            if tile == '.':
                continue
            if position[0].isdigit():
                self.matrix[row][col + i] = tile
            else:
                self.matrix[row + i][col] = tile

    def unplace_tiles(self, position, word):
        row, col = self.get_row_and_col_from_position(position)
        # Unplace the tiles from the board and update the bag
        for i, tile in enumerate(word):
            if tile == '.':
                continue
            if position[0].isdigit():
                self.matrix[row][col + i] = ''
            else:
                self.matrix[row + i][col] = ''

    def get_filled_in_word(self, position, word):
        filled_in_word = ''
        row, col = self.get_row_and_col_from_position(position)

        word_length = len(word)
        # Check for play through tiles
        for i, tile in enumerate(word):
            print_tile = tile
            if tile == '.':
                print_tile = self.matrix[row][col]
                if i == 0:
                    filled_in_word += '('
            
            filled_in_word += print_tile

            if tile == '.' and (i == word_length - 1 or  word[i + 1] != '.'):
                filled_in_word += ')'

            if tile != '.' and i + 1 < word_length and word[i + 1] == '.':
                filled_in_word += '('

            if position[0].isdigit():
                col += 1
            else:
                row += 1

        return filled_in_word

    def save_image(self, gcg_filename, last_play, startx, starty, tile_spacing, board_scale, tile_scale):
        from PIL import Image

        try:
            # 1. Open the base board image
            board_img = Image.open("img/board.jpg").convert("RGB")
            board_orig_w, board_orig_h = board_img.size
            board_new_size = (int(board_orig_w * board_scale), int(board_orig_h * board_scale))
            resized_board_img = board_img.resize(board_new_size, Image.Resampling.LANCZOS)
        except FileNotFoundError:
            print("Error: 'board.jpg' not found in the current directory.")
            return

        # 2. Iterate through the 15x15 board matrix
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                tile_char = self.matrix[row][col]
                
                if tile_char:
                    # GCG blank tiles are lowercase; use uppercase for filenames
                    char_to_load = tile_char.upper()
                    tile_filename = get_unique_image(char_to_load)

                    try:
                        tile_img = Image.open(tile_filename).convert("RGB")
                        
                        # Calculate new dimensions: 1/15th of original height and width
                        orig_w, orig_h = tile_img.size
                        new_size = (int(orig_w * tile_scale), int(orig_h * tile_scale))
                        
                        # Resize the tile in memory using high-quality resampling
                        resized_tile = tile_img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Calculate pixel position based on matrix indices
                        x_pos = startx + (col * tile_spacing)
                        y_pos = starty + (row * tile_spacing)
                        
                        # Overlay the resized letter tile onto the board image
                        resized_board_img.paste(resized_tile, (x_pos, y_pos))
                    except FileNotFoundError:
                        print(f"Warning: Could not find tile image {tile_filename}")

        # 3. Construct filename: "some_name.gcg" -> "some_name_<LAST_PLAY>.jpg"
        base_name = os.path.splitext(gcg_filename)[0]
        output_filename = f"{base_name}{last_play}.jpg"

        # 4. Save the finalized board image
        resized_board_img.save(output_filename, "JPEG")

class Bag:
    def __init__(self):
        self.tiles = {
            "A": 9, "B": 2, "C": 2, "D": 4, "E": 12, "F": 2, "G": 3, "H": 2, "I": 9,
            "J": 1, "K": 1, "L": 4, "M": 2, "N": 6, "O": 8, "P": 2, "Q": 1, "R": 6,
            "S": 4, "T": 6, "U": 4, "V": 2, "W": 2, "X": 1, "Y": 2, "Z": 1, "?": 2
        }

    def remove_tiles(self, word):
        for i, tile in enumerate(word):
            if tile != '.':
                if tile.islower():
                    self.tiles["?"] -= 1
                else:
                    self.tiles[tile] -= 1

    def add_tiles(self, word):
        for i, tile in enumerate(word):
            if tile != '.':
                if tile.islower():
                    self.tiles["?"] += 1
                else:
                    self.tiles[tile] += 1

    def get_string(self):
        bag_string = ""
        for letter in self.tiles:
            letter_was_present = False
            for _ in range(self.tiles[letter]):
                letter_was_present = True
                bag_string += letter
            if letter_was_present:
                bag_string += " "
        bag_string.strip()
        return bag_string
    
    def get_unseen_counts(self):
        unseen_tile_count = 0
        unseen_vowel_count = 0
        for letter in self.tiles:
            for _ in range(self.tiles[letter]):
                unseen_tile_count += 1
                if letter in vowels:
                    unseen_vowel_count += 1
        return unseen_tile_count, unseen_vowel_count

class Game:
    def __init__(self, gcg):
        self.players = Players()
        self.board = Board()
        self.bag = Bag()
        self.previous_player = ""
        self.previous_position = ""
        self.previous_word = ""
        self.previous_move_type = MOVE_TYPE_UNSPECIFIED
        self.blanks = []  # List of (position, tile_designation) tuples
        self.tiles_played = [0, 0]  # Tiles played per player
        self.power_tiles_played = [0, 0]  # Power tiles per player: S, J, Q, X, Z, ?
        self.parse_gcg(gcg)

    def place_tiles(self, position, word):
        self.board.place_tiles(position, word)
        self.bag.remove_tiles(word)
        
        # Track blanks and stats for tile placements
        player_index = self.players.get_index(self.previous_player)
        self._track_blanks_and_stats(position, word, player_index)

    def unplace_tiles(self, position, word):
        player_index = self.players.get_index(self.previous_player)
        for tile in word:
            if tile == '.':
                # Play-through tile, skip
                continue
            
            # Track tiles played (count non-play-through tiles)
            self.tiles_played[player_index] -= 1
            
            # Track blanks (lowercase letters) and count as power tiles
            if tile.islower():
                # Remove the most recently added blank since we're unplacing it
                self.blanks.pop() 
                # Blanks count as power tiles
                self.power_tiles_played[player_index] -= 1
            # Track power tiles
            elif tile.upper() in POWER_TILES_SET:
                self.power_tiles_played[player_index] -= 1

        self.board.unplace_tiles(position, word)
        self.bag.add_tiles(word)

    def remove_tiles(self, word):
        self.bag.remove_tiles(word)

    def _track_blanks_and_stats(self, position, word, player_index):
        """Track blanks and power tiles played."""
        row, col = self.board.get_row_and_col_from_position(position)
        is_horizontal = position[0].isdigit()
        
        
        for i, tile in enumerate(word):
            if tile == '.':
                # Play-through tile, skip
                continue
            
            # Track tiles played (count non-play-through tiles)
            self.tiles_played[player_index] += 1
            
            # Track blanks (lowercase letters) and count as power tiles
            if tile.islower():
                # Calculate the board position for this tile
                if is_horizontal:
                    board_col = col + i
                    board_row = row
                else:
                    board_col = col
                    board_row = row + i
                
                # Convert to GCG notation (1-indexed, column as letter)
                col_letter = chr(ord('A') + board_col)
                row_number = board_row + 1
                
                if is_horizontal:
                    gcg_position = f"{row_number}{col_letter}"
                else:
                    gcg_position = f"{col_letter}{row_number}"
                
                word_with_parens = self.board.get_filled_in_word(self.previous_position, self.previous_word)
                
                self.blanks.append({"position": gcg_position, "tile": tile.upper(), "word": word_with_parens})
                # Blanks count as power tiles
                self.power_tiles_played[player_index] += 1
            # Track power tiles
            elif tile.upper() in POWER_TILES_SET:
                self.power_tiles_played[player_index] += 1

    def parse_gcg(self, gcg):
        with open(gcg, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # print("\n\nline: ", line.strip())
            # Set player 1's name
            match = re.search(r"#player1\s+(\S+)", line)
            if match is not None and match.group(1) is not None and self.players.get_name(0) == "":
                self.players.set_name(0, match.group(1).strip())
                # print(f'team going first: {self.players.get_name(0)}')

            # Set player 2's name
            match = re.search(r"#player2\s+(\S+)", line)
            if match is not None and match.group(1) is not None and self.players.get_name(1) == "":
                self.players.set_name(1, match.group(1).strip())
                # print(f'team going second: {self.players.get_name(1)}')

            # Set final score
            match = re.search(r"^>([^:]+).*\D(\d+)$", line)
            if match is not None and match.group(1) is not None and match.group(2) is not None:
                name = match.group(1).strip()
                score = match.group(2).strip()
                self.players.set_score(name, score)
                # print(f'final score: {name} has {score}')

            # Parse a tile placement move
            match = re.search(r"^>([^:]+):\s+[\w\?]+\s+(\w+)\s+([\w\.]+)\s+(\S+)\s+(\S+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_position = match.group(2).strip()
                self.previous_word = match.group(3).strip()
                self.previous_score = match.group(4).strip()
                self.previous_total = match.group(5).strip()
                self.previous_move_type = MOVE_TYPE_TILE_PLACEMENT
                self.place_tiles(self.previous_position, self.previous_word)
            
            match = re.search(r"^>([^:]+):\s+[\w\?]+\s+-([\w\?]+)\s+(\S+)\s+(\d+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_word = match.group(2).strip()
                self.previous_score = match.group(3).strip()
                self.previous_total = match.group(4).strip()
                self.previous_move_type = MOVE_TYPE_EXCHANGE

            match = re.search(r"^>([^:]+):\s+[\w\?]+\s+-\s+(\S+)\s+(\d+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_score = match.group(2).strip()
                self.previous_total = match.group(3).strip()
                self.previous_move_type = MOVE_TYPE_PASS

            match = re.search(r"^>[^:]+:\s+[\w\?]+\s+--", line)
            if match is not None:
                # print("lost challenge detected, adding tiles back")
                # print(f'previous word: {self.previous_word}')
                self.unplace_tiles(self.previous_position, self.previous_word)

            match = re.search(r"^#rack\d\s([\w\?]+)", line)
            if match is not None and match.group(1) is not None:
                tiles_on_rack = match.group(1).strip()
                # print("tiles_on_rack: ", tiles_on_rack)
                # print(f'tiles on rack: {tiles_on_rack}')
                self.remove_tiles(tiles_on_rack)
            
            self.previous_player = self.previous_player.replace('_', ' ')

    def get_scores_string(self):
        return str(self.players.get_score(0)).rjust(3, '0') + " - " + str(self.players.get_score(1)).rjust(3, '0')
    
    def get_p1_score_string(self):
        return str(self.players.get_score(0)).rjust(3)

    def get_p2_score_string(self):
        return str(self.players.get_score(1)).rjust(3)

    def get_unseen_tiles_string(self):
        return self.bag.get_string()

    def get_unseen_count_string(self):
        unseen_tile_count, unseen_vowel_count = self.bag.get_unseen_counts()
        unseen_consonant_count = unseen_tile_count - unseen_vowel_count
        tile_word = "tile" if unseen_tile_count == 1 else "tiles"
        count_string = str(unseen_tile_count) + " " + tile_word + "\n"
        vowel_word = "vowel" if unseen_vowel_count == 1 else "vowels"
        count_string += str(unseen_vowel_count).rjust(2) + " " + vowel_word + " | "
        consonant_word = "consonant" if unseen_consonant_count == 1 else "consonants"
        count_string += str(unseen_consonant_count).rjust(2) + " " + consonant_word
        return count_string

    def get_last_play_string(self, word_definitions, lex_symbols_map):
        if self.previous_move_type == MOVE_TYPE_UNSPECIFIED:
            return ""
        elif self.previous_move_type == MOVE_TYPE_TILE_PLACEMENT:
            word_with_parens = self.board.get_filled_in_word(self.previous_position, self.previous_word)
            word_without_parens = re.sub(r'[^A-Za-z]', '', word_with_parens.upper())
            word_definition = get_word_definition(word_definitions, word_without_parens)
            lex_symbols = lex_symbols_map.get(word_without_parens, "")
            display_word = word_with_parens + lex_symbols
            return f'{LAST_PLAY_PREFIX}{self.previous_player} {self.previous_position} {display_word} {self.previous_score} {self.previous_total} | {word_definition}'
        elif self.previous_move_type == MOVE_TYPE_EXCHANGE:
            return f'{LAST_PLAY_PREFIX}{self.previous_player} exch {self.previous_word} {self.previous_score} {self.previous_total}'
        elif self.previous_move_type == MOVE_TYPE_PASS:
            return f'{LAST_PLAY_PREFIX}{self.previous_player} pass {self.previous_score} {self.previous_total}'
        raise ValueError(f'Unknown move type: {self.previous_move_type}')

    def get_blank_1_string(self):
        """Return blank 1 info if it exists."""
        if len(self.blanks) >= 1:
            return self.blanks[0]["word"]
        return ""
    
    def get_blank_2_string(self):
        """Return blank 2 info if it exists."""
        if len(self.blanks) >= 2:
            return self.blanks[1]["word"]
        
        return ""
    
    def get_stats1_string(self):
        """Return player 1 stats: tiles played and power tiles played."""
        return f"Tiles: {self.tiles_played[0]}\nPower: {self.power_tiles_played[0]}"
    
    def get_stats2_string(self):
        """Return player 2 stats: tiles played and power tiles played."""
        return f"Tiles: {self.tiles_played[1]}\nPower: {self.power_tiles_played[1]}"

    def save_image(self, gcg_filename, startx, starty, tile_spacing, board_scale, tile_scale):
        last_play = ""
        if self.previous_move_type != MOVE_TYPE_UNSPECIFIED:
            word_with_parens = self.board.get_filled_in_word(self.previous_position, self.previous_word)
            last_play = "_" + re.sub(r'[^A-Za-z]', '', word_with_parens.upper())
        return self.board.save_image(gcg_filename, last_play, startx, starty, tile_spacing, board_scale, tile_scale)

def read_definitions(filename):
    word_definitions = {}
    lex_symbols_map = {} 
    with open(filename, 'r') as file:
        for line in file:
            parts = line.strip().split(",", 1)
            if len(parts) != 2:
                raise ValueError(f'Invalid definition: {line}')
            raw_word = parts[0]                      
            definition = parts[1].strip()            
            definition = definition[1:-1]        
            key = _clean_csv_key(raw_word)

            # Extract lexicon symbols exactly as they appear in the CSV (after the cleaned key)
            m = LEX_SUFFIX_RE.search(raw_word)
            lex_symbols = m.group(0) if m else ""

            word_definitions[key] = definition
            lex_symbols_map[key] = lex_symbols

    return word_definitions, lex_symbols_map

def get_word_definition(word_definitions, word):
    if word in word_definitions:
        return word_definitions[word]
    # print(f'No definition found for {word}')
    return ""

async def _drain_magpie(proc, timeout=0.5):
    """Read all available lines from proc.stdout within the given timeout window."""
    collected = []
    while True:
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if line:
                decoded = line.decode(errors='replace')
                _magpie_debug(f"[MAGPIE] {decoded}", end='', flush=True)
                collected.append(decoded)
        except asyncio.TimeoutError:
            break
    return ''.join(collected)


async def _wait_for_magpie_finished(proc, timeout=5.0):
    """Read stdout lines until a 'finished' line is seen, or until timeout/EOF."""
    collected = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            if not line:  # EOF
                break
            decoded = line.decode(errors='replace')
            _magpie_debug(f"[MAGPIE] {decoded}", end='', flush=True)
            collected.append(decoded)
            if 'finished' in decoded or 'error' in decoded.lower():
                break
        except asyncio.TimeoutError:
            break
    return ''.join(collected)


def _magpie_warn_and_disable(proc, context, output):
    """Print a prominent autosim warning, kill the process, and return None."""
    print(
        "\n" + "=" * 60 + "\n"
        "!!! AUTOSIM WARNING !!!\n"
        f"MAGPIE reported a problem during {context}.\n"
        "Autosim has been DISABLED. The rest of the program will\n"
        "continue running normally without automatic analysis.\n"
        f"\nMAGPIE output:\n{output.strip()}\n"
        + "=" * 60 + "\n",
        flush=True
    )
    proc.kill()
    return None


def _magpie_output_ok(output):
    return 'finished' in output and 'error' not in output.lower()


async def _run_magpie_analysis(proc, gcg_filename, game, poll_interval=1.0):
    """Load the current GCG into MAGPIE, run analysis, and write results to analysis.txt."""
    try:
        unseen_count, _ = game.bag.get_unseen_counts()
        command = 'endgame' if unseen_count <= 7 else 'gs'
        final_cmd = 'she' if command == 'endgame' else 'shm'

        gcg_abs = os.path.abspath(gcg_filename)
        _magpie_debug(f"[MAGPIE] starting analysis: unseen={unseen_count}, command={command}", flush=True)

        proc.stdin.write(f'load {gcg_abs}\n'.encode())
        await proc.stdin.drain()
        _magpie_debug("[MAGPIE] sent load, waiting for finished", flush=True)
        load_output = await _wait_for_magpie_finished(proc)
        if not _magpie_output_ok(load_output):
            _magpie_warn_and_disable(proc, 'load', load_output)
            return

        proc.stdin.write(b'goto end\n')
        await proc.stdin.drain()
        _magpie_debug("[MAGPIE] sent goto end, waiting for finished", flush=True)
        goto_output = await _wait_for_magpie_finished(proc)
        if not _magpie_output_ok(goto_output):
            _magpie_warn_and_disable(proc, 'goto end', goto_output)
            return

        proc.stdin.write(f'{command}\n'.encode())
        await proc.stdin.drain()
        _magpie_debug(f"[MAGPIE] sent {command}", flush=True)

        await asyncio.sleep(0.2)

        proc.stdin.write(b'status\n')
        await proc.stdin.drain()
        _magpie_debug("[MAGPIE] sent initial status", flush=True)

        while True:
            await asyncio.sleep(poll_interval)
            output = await _drain_magpie(proc, timeout=0.1)
            if output:
                with open('analysis.txt', 'w') as f:
                    f.write(output)
            if '(error 1)' in output or 'finished' in output:
                _magpie_debug(f"[MAGPIE] command finished, fetching result with {final_cmd}", flush=True)
                proc.stdin.write(f'{final_cmd}\n'.encode())
                await proc.stdin.drain()
                final_output = await _drain_magpie(proc, timeout=2.0)
                with open('analysis.txt', 'w') as f:
                    f.write(final_output)
                _magpie_debug("[MAGPIE] analysis.txt written", flush=True)
                break
            proc.stdin.write(b'status\n')
            await proc.stdin.drain()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        import traceback
        _magpie_debug(f"[MAGPIE] analysis task error: {e}", flush=True)
        if AUTOSIM_DEBUG:
            traceback.print_exc()


async def main(
        gcg_filename,
        lex_filename, 
        score_output_filename, 
        unseen_output_filename, 
        count_output_filename, 
        last_play_output_filename, 
        blank1_output_filename=None,
        blank2_output_filename=None,
        stats1_output_filename=None,
        stats2_output_filename=None,
        ver="std", 
        p1score=None, 
        p2score=None,
        tilestartx=50,
        tilestarty=50,
        tilespacing=50,
        boardscale=1.0,
        tilescale=1.0,
        saveboardimg=False,
        autosim_path=None
        ):
    
    from watchfiles import awatch

    word_definitions, lex_symbols_map = read_definitions(lex_filename)

    magpie_proc = None
    analysis_task = None
    if autosim_path:
        lex_stem = Path(lex_filename).stem  # e.g. "NWL23defs"
        lex = re.sub(r'defs$', '', lex_stem, flags=re.IGNORECASE)  # e.g. "NWL23"
        magpie_proc = await asyncio.create_subprocess_exec(
            './bin/magpie',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=autosim_path,
        )
        startup_output = await _wait_for_magpie_finished(magpie_proc)
        if not _magpie_output_ok(startup_output):
            magpie_proc = _magpie_warn_and_disable(magpie_proc, 'startup', startup_output)
        else:
            initial_config = f'set -lex {lex} -ld english -printonf true -shwithmoves false -minp 200 -numplays 200 -eplies 25\n'
            magpie_proc.stdin.write(initial_config.encode())
            await magpie_proc.stdin.drain()
            set_output = await _wait_for_magpie_finished(magpie_proc)
            if not _magpie_output_ok(set_output):
                magpie_proc = _magpie_warn_and_disable(magpie_proc, 'initial configuration', set_output)

    print(
        f"\n\n\n!!! SUCCESS !!!\nSuccessfully starting watching {gcg_filename} for changes.\n"
        "On certain operating systems you might see syntax warnings above which can be safely ignored.\n"
        "This script is designed to run indefinitely watching for changes to the GCG file,\n"
        "so while it's running you will be unable to enter commands in this terminal.\n"
        "Any syntax or error messages after this message are legitimate and should be reported to the developer.\n"
        "To stop execution, hit control-C.\n"
    )

    async for _ in awatch(gcg_filename):
        game = Game(gcg_filename)

        if ver == "au":
            if p1score and p2score:
                p1_path = p1score
                p2_path = p2score
            else:
                # making sure no issues if someone passes in a path for --ver au
                out_dir = os.path.dirname(score_output_filename) or "."
                base = os.path.basename(score_output_filename)
                p1_path = os.path.join(out_dir, "p1_" + base)  
                p2_path = os.path.join(out_dir, "p2_" + base)

            with open(p1_path, "w", encoding="utf-8") as score_file:
                score_file.write(game.get_p1_score_string())

            with open(p2_path, "w", encoding="utf-8") as score_file:
                score_file.write(game.get_p2_score_string())
        else:
            # Standard mode: write one file with both scores
            with open(score_output_filename, "w", encoding="utf-8") as score_file:
                score_file.write(game.get_scores_string())

        with open(unseen_output_filename, "w") as unseen_file:
            unseen_file.write(game.get_unseen_tiles_string())

        with open(count_output_filename, "w") as count_file:
            count_file.write(game.get_unseen_count_string())

        with open(last_play_output_filename, "w") as last_play_file:
            last_play_file.write(game.get_last_play_string(word_definitions, lex_symbols_map))

        # Write blank files if they exist
        if blank1_output_filename:
            blank1_content = game.get_blank_1_string()
            with open(blank1_output_filename, "w") as blank1_file:
                blank1_file.write(blank1_content)
        
        if blank2_output_filename:
            blank2_content = game.get_blank_2_string()
            with open(blank2_output_filename, "w") as blank2_file:
                blank2_file.write(blank2_content)
        
        # Write stats files if provided
        if stats1_output_filename:
            with open(stats1_output_filename, "w") as stats1_file:
                stats1_file.write(game.get_stats1_string())
        
        if stats2_output_filename:
            with open(stats2_output_filename, "w") as stats2_file:
                stats2_file.write(game.get_stats2_string())

        if saveboardimg:
            game.save_image(gcg_filename, tilestartx, tilestarty, tilespacing, boardscale, tilescale)

        if autosim_path and magpie_proc:
            if analysis_task and not analysis_task.done():
                analysis_task.cancel()
                try:
                    await analysis_task
                except asyncio.CancelledError:
                    pass
            magpie_proc.stdin.write(b'stop\n')
            await magpie_proc.stdin.drain()
            await _drain_magpie(magpie_proc, timeout=0.5)
            analysis_task = asyncio.create_task(
                _run_magpie_analysis(magpie_proc, gcg_filename, game)
            )

async def run_watcher(args):
    await main(
        args.gcg, 
        args.lex, 
        args.score, 
        args.unseen, 
        args.count, 
        args.lp, 
        getattr(args, 'blank1', None),
        getattr(args, 'blank2', None),
        getattr(args, 'stats1', None),
        getattr(args, 'stats2', None),
        args.ver, 
        args.p1score, 
        args.p2score,
        args.tilestartx,
        args.tilestarty,
        args.tilespacing,
        args.boardscale,
        args.tilescale,
        args.saveboardimg,
        getattr(args, 'autosim', None)
    )

def build_cli_parser():
    p = argparse.ArgumentParser(add_help=False)  # we'll add help in the top-level parser
    p.add_argument("--gcg", type=str, help="the gcg file to monitor")
    p.add_argument("--lex", type=str, help="the lexicon file to use for definitions")
    p.add_argument("--score", type=str, help="the output file(s) to write the score")
    p.add_argument("--p1score", type=str, help="(au optional) explicit Player 1 score output file")
    p.add_argument("--p2score", type=str, help="(au optional) explicit Player 2 score output file")
    p.add_argument("--unseen", type=str, help="the output file to write the unseen tiles")
    p.add_argument("--count", type=str,  help="the output file to write the number of unseen tiles and vowel to consonant ratio")
    p.add_argument("--lp", type=str, help="the output file to write the last play")
    p.add_argument("--blank1", type=str, help="the output file to write the first blank (if any)")
    p.add_argument("--blank2", type=str, help="the output file to write the second blank (if any)")
    p.add_argument("--stats1", type=str, help="the output file to write player 1 game stats (tiles and power tiles)")
    p.add_argument("--stats2", type=str, help="the output file to write player 2 game stats (tiles and power tiles)")
    p.add_argument("--ver", choices=["std", "au"], default="std",
                   help="Output format: 'std' (default) outputs one file with both scores; 'au' writes p1_*/p2_* files")
    
    # Optional layout arguments
    p.add_argument("--tilestartx", type=int, default=50, help="Horizontal offset of the first tile in the board image")
    p.add_argument("--tilestarty", type=int, default=50, help="Vertical offset of the first tile in the board image")
    p.add_argument("--tilespacing", type=int, default=50, help="Spacing between tiles in the board image")
    p.add_argument("--boardscale", type=float, default=1.0, help="Scale of the board in the board image")
    p.add_argument("--tilescale", type=float, default=1.0, help="Scale of the tiles in the board image")
    p.add_argument("--saveboardimg", action="store_true", help="Output board images")
    p.add_argument("--autosim", type=str, default=None, help="Path to MAGPIE directory for automatic analysis after each GCG update")
    return p

def run_gui():
    import json
    import os
    import platform
    import queue
    import shutil
    import signal
    import sys
    import threading
    from pathlib import Path
    from datetime import datetime

    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

# -------------------------------
# Persistent config
# -------------------------------
    APP_NAME = "WatchGCG-GUI"
    CONFIG_DIR = os.path.join(Path.home(), f".{APP_NAME.lower()}")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "folders.json")

    FOLDER_KEYS = {
        "gcg":   "Last folder used for GCG files",
        "lex":   "Last folder used for Lexicon CSV/TXT",
        "score": "Last folder used for Score output",
        "unseen":"Last folder used for Unseen tiles output",
        "count": "Last folder used for Unseen count output",
        "lp":    "Last folder used for Last-play output",
        "blank1":"Last folder used for Blank 1 output",
        "blank2":"Last folder used for Blank 2 output",
        "stats1":"Last folder used for Stats 1 output",
        "stats2":"Last folder used for Stats 2 output",
    }

    SUCCESS_MARK = "To stop execution, hit control-C."  # gate log output

    # -------------------------------
    # Folder memory helpers
    # -------------------------------
    def load_all_folders():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_last_folder(folder_path, key="last_folder"):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = load_all_folders()
        data[key] = folder_path
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_last_folder(key="last_folder"):
        data = load_all_folders()
        return data.get(key)

    # -------------------------------
    # Runner that spawns watch_gcg.py (shows only post-success logs)
    # -------------------------------
    class TailRunner:
        def __init__(self, on_log):
            self.on_log = on_log
            self.proc = None
            self.q = queue.Queue()
            self.thread = None
            self.show_after_success = False
            self._gcg_display = None

        def start(self, python_exe, script_path, args, gcg_path=None):
            if self.proc:
                self.on_log("[warn] Already running.\n")
                return
            
            if not python_exe:
                python_exe = sys.executable or "py"

            self._gcg_display = Path(gcg_path).name if gcg_path else None
            cmd = [python_exe, "-u", script_path] + args
            self.on_log(f"[info] Launching: {' '.join(cmd)}\n")

            def reader():
                try:
                    self.proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                    )
                    # Stream stdout lines
                    for raw in self.proc.stdout:
                        line = raw if raw is not None else ""
                        if not self.show_after_success and SUCCESS_MARK in line:
                            self.show_after_success = True
                            gcg_filename = self._gcg_display or "the selected GCG file"
                            self.q.put(f"\n\n\n!!! SUCCESS !!!\nSuccessfully starting watching {gcg_filename} for changes.\n"
                                    "Any syntax or error messages after this message are legitimate and should be reported to the developer.\n"
                                    "To stop execution, exit out of this window.\n")
                            continue
                        if self.show_after_success:
                            self.q.put(line)
                except FileNotFoundError:
                    self.q.put("[error] Could not start Python or script.\n")
                finally:
                    self.q.put("[info] Process exited.\n")

            self.thread = threading.Thread(target=reader, daemon=True)
            self.thread.start()

        def poll(self):
            try:
                while True:
                    self.on_log(self.q.get_nowait())
            except queue.Empty:
                pass

        def stop(self):
            if not self.proc:
                return
            try:
                if os.name == "nt":
                    # Graceful on Windows
                    self.proc.terminate()
                else:
                    self.proc.send_signal(signal.SIGTERM)
            except Exception:
                pass
            self.proc = None
            self.thread = None
            self.show_after_success = False
        
    # -------------------------------
    # Main GUI
    # -------------------------------
    class App(ttk.Frame):
        def __init__(self, master):
            super().__init__(master)
            master.title("WatchGCG")
            master.geometry("780x560")
            master.minsize(700, 520)
            self.pack(fill="both", expand=True)

            os.makedirs(CONFIG_DIR, exist_ok=True)

            # Build UI
            self._make_file_picker_section()
            self._make_controls()
            self._make_log()

            # Validate python exe
            py = (self.python_var.get() or "").strip()
            if not py:
                py = sys.executable  # fallback

            def _looks_like_python_exe(p):
                base = os.path.basename(p).lower()
                return base in ("python.exe", "pythonw.exe", "py.exe", "pyw.exe") or base.startswith("python") and base.endswith(".exe")

            # If user accidentally picked the script or a folder, warn
            if os.path.isdir(py) or (py.lower().endswith(".py") and os.path.exists(py)) or (os.name == "nt" and not _looks_like_python_exe(py) and py not in ("py", "python", "python3")):
                messagebox.showwarning(
                    "Invalid Python",
                    "The 'Python exe' field must point to a Python interpreter (python.exe) or be 'py'."
                )
                return
            
            # Runner + polling
            self.runner = TailRunner(self._append_log)
            self.after(120, self._poll_runner)

            # Stop child on window close
            master.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---------- UI: file pickers ----------
        def _make_file_picker_section(self):
            self.inputs = {}

            frm = ttk.LabelFrame(self, text="Paths")
            frm.pack(fill="x", padx=10, pady=10)

            # --- Version row (dropdown) ---
            ver_row = ttk.Frame(frm)
            ver_row.pack(fill="x", padx=8, pady=6)

            ttk.Label(ver_row, text="Version", width=28).pack(side="left")
            self.ver_labels = {"Default": "std", "Australian": "au"}
            self.ver_var = tk.StringVar(value="Default")  # user-facing label

            ver_combo = ttk.Combobox(
                ver_row,
                textvariable=self.ver_var,
                state="readonly",
                width=20,
                values=list(self.ver_labels.keys())  # ["Default", "Australian"]
            )
            ver_combo.pack(side="left")
            ver_combo.bind("<<ComboboxSelected>>", lambda e: self._on_version_change())
            
            # --- Paths frame ---
            self.paths_frame = ttk.Frame(frm)
            self.paths_frame.pack(fill="x")

            # Build rows into self.paths_frame to show/hide subsets
            self._build_path_rows(self.paths_frame)

            # Initialize visibility
            self._on_version_change()

        def _build_path_rows(self, frm):
            
            fields = [
                ("gcg",   "GCG file (.gcg)",          [("GCG file", "*.gcg")]),
                ("lex",   "Lexicon file (.csv)",      [("Lexicon", "*.csv")]),
                # Score field (single) for Default
                ("score", "Score (.txt)",             [("Score", "*.txt")]),
                # AU fields (two) – initially hidden
                ("p1score", "Player 1 Score (.txt)",  [("Player 1 Score", "*.txt")]),
                ("p2score", "Player 2 Score (.txt)",  [("Player 2 Score", "*.txt")]),
                ("unseen","Unseen tiles (.txt)",      [("Unseen Tiles", "*.txt")]),
                ("count", "Unseen count (.txt)",      [("Unseen Count", "*.txt")]),
                ("lp",    "Last play (.txt)",         [("Last Play", "*.txt")]),
                ("blank1","Blank 1 (.txt)",           [("Blank 1", "*.txt")]),
                ("blank2","Blank 2 (.txt)",           [("Blank 2", "*.txt")]),
                ("stats1","Stats 1 (.txt)",           [("Stats 1", "*.txt")]),
                ("stats2","Stats 2 (.txt)",           [("Stats 2", "*.txt")]),
            ]

            self._row_widgets = {}

            for key, label, patterns in fields:
                row = ttk.Frame(frm)
                row.pack(fill="x", padx=8, pady=6)

                ttk.Label(row, text=label, width=28).pack(side="left")
                var = tk.StringVar()
                ent = ttk.Entry(row, textvariable=var)
                ent.pack(side="left", fill="x", expand=True, padx=(0, 8))

                def make_browse(k=key, pats=patterns, evar=var, dialog_label=label):
                    def browse():
                        lastdir = load_last_folder(k) or os.getcwd()
                        path = filedialog.askopenfilename(
                            parent=self,
                            title=f"Choose {dialog_label}",
                            initialdir=lastdir,
                            filetypes=pats
                        )

                        if path:
                            evar.set(path)
                            save_last_folder(os.path.dirname(path), k)
                    return browse

                ttk.Button(row, text="Browse…", command=make_browse()).pack(side="left")

                self.inputs[key] = var
                self._row_widgets[key] = row

        def _on_version_change(self):
            label = self.ver_var.get()
            mode = self.ver_labels.get(label, "std")

            if mode == "std":
                self._row_widgets["score"].pack(fill="x", padx=8, pady=6)
                self._row_widgets["p1score"].pack_forget()
                self._row_widgets["p2score"].pack_forget()
                # show before unseen
                self._row_widgets["score"].pack(
                    before=self._row_widgets["unseen"], fill="x", padx=8, pady=6
                )
            else:
                self._row_widgets["score"].pack_forget()
                self._row_widgets["p1score"].pack(
                    before=self._row_widgets["unseen"], fill="x", padx=8, pady=6)
                self._row_widgets["p2score"].pack(
                    before=self._row_widgets["unseen"], fill="x", padx=8, pady=6)
        
            self.mode = mode


        # ---------- UI: controls ----------
        def _make_controls(self):
            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=10, pady=(0, 10))

            self.python_var = tk.StringVar(value=sys.executable or "python")
            ttk.Label(bar, text="Python exe:").pack(side="left")
            py_entry = ttk.Entry(bar, textvariable=self.python_var, width=42)
            py_entry.pack(side="left", padx=(4, 10))

            def choose_python():
                kw = {}
                if os.name == "nt":
                    kw["filetypes"] = [("Python executable", "python*.exe"), ("Executables", "*.exe"), ("All files", "*.*")]
                path = filedialog.askopenfilename(title="Choose Python executable", **kw)
                if path:
                    self.python_var.set(path)
            ttk.Button(bar, text="Find…", command=choose_python).pack(side="left", padx=(0, 12))

            ttk.Button(bar, text="Start", command=self.on_start).pack(side="right")
          

        # ---------- UI: log ----------
        def _make_log(self):
            logfrm = ttk.LabelFrame(self, text="Log")
            logfrm.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            btnbar = ttk.Frame(logfrm)
            btnbar.pack(side="bottom",fill="x", padx=8, pady=(0, 8))
            ttk.Button(btnbar, text="Copy log", command=self._copy_log).pack(side="left")
            ttk.Button(btnbar, text="Clear", command=self._clear_log).pack(side="left", padx=(6, 0))

            self.log_text = tk.Text(logfrm, wrap="word", height=18, state="disabled")
            self.log_text.pack(fill="both", expand=True, padx=8, pady=8)


        def _append_log(self, s: str):
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{ts}] {s}")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        def _copy_log(self):
            text = self.log_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Log copied to clipboard.")

        def _clear_log(self):
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

        # ---------- Start / stop ----------
        def on_start(self):
            vals = {k: v.get().strip() for k, v in self.inputs.items()}
            mode = getattr(self, "mode", "std")
           
            # Validate required fields
            missing = []
            base_required = ["gcg", "lex", "unseen", "count", "lp"]
            if mode == "std":
                base_required.append("score")
            else:
                # AU requires both p1/p2 explicitly (GUI does not derive from single score file)
                if not (vals.get("p1score") and vals.get("p2score")):
                    missing.append("p1score & p2score")
            # check base fields
            for k in base_required:
                if not vals.get(k):
                    missing.append(k)

            if missing:
                messagebox.showwarning("Missing fields", f"Please choose files for: {', '.join(missing)}")
                return

            script_path = os.path.abspath(__file__)
            args = [
                "--gcg", vals["gcg"],
                "--lex", vals["lex"],
                "--unseen", vals["unseen"],
                "--count", vals["count"],
                "--lp", vals["lp"],
                "--ver", mode,
            ]

            if mode == "std":
                args += ["--score", vals["score"]]
            else:
                # Because GUI always requires two files explicitly in AU mode
                args += ["--p1score", vals["p1score"], "--p2score", vals["p2score"]]

            # Add optional blank and stats files if provided
            if vals.get("blank1"):
                args += ["--blank1", vals["blank1"]]
            if vals.get("blank2"):
                args += ["--blank2", vals["blank2"]]
            if vals.get("stats1"):
                args += ["--stats1", vals["stats1"]]
            if vals.get("stats2"):
                args += ["--stats2", vals["stats2"]]

            # Persist folders
            for k, v in vals.items():
                if v:
                    save_last_folder(os.path.dirname(v), k)

            self.runner.start(self.python_var.get(), script_path, args, gcg_path=vals["gcg"])
        
        def _on_close(self):
            self.runner.stop()
            self.master.destroy()

        # ---------- Poll runner ----------
        def _poll_runner(self):
            self.runner.poll()
            self.after(120, self._poll_runner)
        
    def _gui_main():
        root = tk.Tk()
        try: root.call("tk", "scaling", 1.25)
        except Exception: pass
        style = ttk.Style(root)
        try:
            if "vista" in style.theme_names():
                style.theme_use("vista")
        except Exception:
            pass
        App(root)
        root.mainloop()

    _gui_main()

def parse_top_level(argv):
    # top-level parser to catch --gui & forward the rest
    top = argparse.ArgumentParser(prog="watch_gcg", add_help=True)
    top.add_argument("--gui", action="store_true", help="Launch the GUI")
    # pass the rest to the CLI parser
    known, rest = top.parse_known_args(argv)
    return known, rest

if __name__ == "__main__":
    ensure_requirements()
    known, rest = parse_top_level(sys.argv[1:])
    if known.gui or not rest:
        # GUI mode if --gui OR if no other args given
        try:
            run_gui()
        except Exception as e:
            # Surface errors instead of a silent close on double-click
            if os.name == "nt":
                try:
                    import ctypes, traceback
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        f"{traceback.format_exc()}",
                        "WatchGCG – startup error",
                        0x00000010,  # MB_ICONHAND
                    )
                except Exception:
                    pass
            raise
    else:
        cli = build_cli_parser().parse_args(rest)
        if cli.saveboardimg:
            ensure_pil()

        for required_inputs in ("gcg", "lex", "unseen", "count", "lp"):
            if not getattr(cli, required_inputs, None):
                print(f"required: {required_inputs}"); sys.exit(-1)

        if cli.ver == "au":
            # Must have either BOTH explicit p1/p2 OR a single --score (to derive p1_/p2_)
            if (bool(cli.p1score) ^ bool(cli.p2score)):  # xor -> only one given
                print("Error: Must provide BOTH --p1score and --p2score or neither for Australian version.")
                sys.exit(-1)
            if not ( (cli.p1score and cli.p2score) or cli.score ):
                print("Error: Either provide BOTH --p1score and --p2score, or ONE --score to derive p1_/p2_ files.")
                sys.exit(-1)
        else:
            if not cli.score:
                print("required: score"); sys.exit(-1)
        try:
            asyncio.run(run_watcher(cli))
        except KeyboardInterrupt:
            print("\n\nDetected Ctrl-C from user input, stopping script.\n")
