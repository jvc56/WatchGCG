import re
import argparse
import asyncio
from watchfiles import awatch

vowels = "aeiouyAEIOUY"
BOARD_SIZE = 15
MOVE_TYPE_UNSPECIFIED = 0
MOVE_TYPE_TILE_PLACEMENT = 1
MOVE_TYPE_EXCHANGE = 2
MOVE_TYPE_PASS = 3

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
        self.parse_gcg(gcg)

    def place_tiles(self, position, word):
        self.board.place_tiles(position, word)
        self.bag.remove_tiles(word)

    def unplace_tiles(self, position, word):
        self.board.unplace_tiles(position, word)
        self.bag.add_tiles(word)

    def remove_tiles(self, word):
        self.bag.remove_tiles(word)

    def parse_gcg(self, gcg):
        with open(gcg, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # print("\n\nline: ", line.strip())
            # Set player 1's name
            match = re.search("#player1\s+(\S+)", line)
            if match is not None and match.group(1) is not None and self.players.get_name(0) == "":
                self.players.set_name(0, match.group(1).strip())
                # print(f'team going first: {self.players.get_name(0)}')

            # Set player 2's name
            match = re.search("#player2\s+(\S+)", line)
            if match is not None and match.group(1) is not None and self.players.get_name(1) == "":
                self.players.set_name(1, match.group(1).strip())
                # print(f'team going second: {self.players.get_name(1)}')

            # Set final score
            match = re.search("^>([^:]+).*\D(\d+)$", line)
            if match is not None and match.group(1) is not None and match.group(2) is not None:
                name = match.group(1).strip()
                score = match.group(2).strip()
                self.players.set_score(name, score)
                # print(f'final score: {name} has {score}')

            # Parse a tile placement move
            match = re.search("^>([^:]+):\s+[\w\?]+\s+(\w+)\s+([\w\.]+)\s+(\S+)\s+(\S+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_position = match.group(2).strip()
                self.previous_word = match.group(3).strip()
                self.previous_score = match.group(4).strip()
                self.previous_total = match.group(5).strip()
                self.previous_move_type = MOVE_TYPE_TILE_PLACEMENT
                self.place_tiles(self.previous_position, self.previous_word)
            
            match = re.search("^>([^:]+):\s+[\w\?]+\s+-([\w\?]+)\s+(\S+)\s+(\d+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_word = match.group(2).strip()
                self.previous_score = match.group(3).strip()
                self.previous_total = match.group(4).strip()
                self.previous_move_type = MOVE_TYPE_EXCHANGE

            match = re.search("^>([^:]+):\s+[\w\?]+\s+-\s+(\S+)\s+(\d+)", line)
            if match is not None and match.group(1) is not None:
                self.previous_player = match.group(1).strip()
                self.previous_score = match.group(2).strip()
                self.previous_total = match.group(3).strip()
                self.previous_move_type = MOVE_TYPE_PASS

            match = re.search("^>[^:]+:\s+[\w\?]+\s+--", line)
            if match is not None:
                # print("lost challenge detected, adding tiles back")
                # print(f'previous word: {self.previous_word}')
                self.unplace_tiles(self.previous_position, self.previous_word)

            match = re.search("^#rack\d\s([\w\?]+)", line)
            if match is not None and match.group(1) is not None:
                tiles_on_rack = match.group(1).strip()
                # print("tiles_on_rack: ", tiles_on_rack)
                # print(f'tiles on rack: {tiles_on_rack}')
                self.remove_tiles(tiles_on_rack)

    def get_scores_string(self):
        return str(self.players.get_score(0)).rjust(3) + " - " + str(self.players.get_score(1)).ljust(3)

    def get_unseen_tiles_string(self):
        return self.bag.get_string()

    def get_unseen_count_string(self):
        unseen_tile_count, unseen_vowel_count = self.bag.get_unseen_counts()
        count_string = str(unseen_tile_count) + " tiles\n"
        count_string += str(unseen_vowel_count).rjust(2) + " vowels | "
        count_string += str(unseen_tile_count - unseen_vowel_count).rjust(2) + " consonants"
        return count_string

    def get_previous_filled_in_word(self):
        return self.board.get_filled_in_word(self.previous_position, self.previous_word)

    def get_previous_filled_in_word_without_parens(self):
        word_with_parens = self.get_previous_filled_in_word()
        return re.sub(r'[^A-Za-z]', '', word_with_parens.upper())

    def get_last_play_string(self):
        if self.previous_move_type == MOVE_TYPE_UNSPECIFIED:
            raise ValueError("No previous move detected")
        elif self.previous_move_type == MOVE_TYPE_TILE_PLACEMENT:
            previous_filled_in_word = self.get_previous_filled_in_word()
            return f'{self.previous_player}: {self.previous_position} {previous_filled_in_word} {self.previous_score} {self.previous_total}'
        elif self.previous_move_type == MOVE_TYPE_EXCHANGE:
            return f'{self.previous_player}: exch {self.previous_word} {self.previous_score} {self.previous_total}'
        elif self.previous_move_type == MOVE_TYPE_PASS:
            return f'{self.previous_player}: pass {self.previous_score} {self.previous_total}'
        raise ValueError(f'Unknown move type: {self.previous_move_type}')

def read_definitions(filename):
    word_definitions = {}
    with open(filename, 'r') as file:
        for line in file:
            word, definition = line.strip().split('\t', 1)
            word_definitions[word] = definition
    return word_definitions

def get_word_definition(word_definitions, word):
    if word in word_definitions:
        return word_definitions[word]
    # print(f'No definition found for {word}')
    return ""

async def main(gcg_filename, lex_filename, score_output_filename, unseen_output_filename, count_output_filename, last_play_output_filename, dfn_output_filename):
    word_definitions = read_definitions(lex_filename)
    async for _ in awatch(gcg_filename):
        game = Game(gcg_filename)

        # print("scores: " + game.get_scores_string())
        # print("unseen: " + game.get_unseen_tiles_string())
        # print("count: " + game.get_unseen_count_string())
        # print("last play: " + game.get_last_play_string())

        with open(score_output_filename, "w") as score_file:
            score_file.write(game.get_scores_string())
    
        with open(unseen_output_filename, "w") as unseen_file:
            unseen_file.write(game.get_unseen_tiles_string())

        with open(count_output_filename, "w") as count_file:
            count_file.write(game.get_unseen_count_string())

        with open(last_play_output_filename, "w") as last_play_file:
            last_play_file.write(game.get_last_play_string())

        with open(dfn_output_filename, "w") as dfn_file:
            dfn_file.write(get_word_definition(word_definitions, game.get_previous_filled_in_word_without_parens()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcg", type=str, help="the gcg file to monitor")
    parser.add_argument("--lex", type=str, help="the lexicon file to use for definitions")
    parser.add_argument("--score", type=str, help="the output file to write the score")
    parser.add_argument("--unseen", type=str, help="the output file to write the unseen tiles")
    parser.add_argument("--count", type=str, help="the output file to write the number of unseen tiles and vowel to consonant ratio")
    parser.add_argument("--lp", type=str, help="the output file to write the last play")
    parser.add_argument("--dfn", type=str, help="the output file to write the definition")
    args = parser.parse_args()

    if not args.gcg:
        print("required: gcg")
        exit(-1)

    if not args.score:
        print("required: score")
        exit(-1)

    if not args.unseen:
        print("required: unseen")
        exit(-1)

    if not args.count:
        print("required: count")
        exit(-1)

    if not args.lp:
        print("required: lp")
        exit(-1)

    if not args.lex:
        print("required: lex")
        exit(-1)

    if not args.lex:
        print("required: dfn")
        exit(-1)

    asyncio.run(main(args.gcg, args.lex, args.score, args.unseen, args.count, args.lp, args.dfn))