import sys
import os

def get_output_filename(column_name, player_number):
    return f"player{player_number}_{column_name}.txt"

def write_single_file(column_name, player_number, content):
    with open(get_output_filename(column_name, player_number), 'w') as file:
        file.write(content)

def write_player_data(player_info, header, player_index, player_number):
    player_info_row = player_info[player_index]
    for index, column_name in enumerate(header):
        write_single_file(column_name, player_number, player_info_row[index])

def parse_player_csv(csv_filename, player1_index, player2_index):
    # Check if the CSV file exists
    if not os.path.isfile(csv_filename):
        raise ValueError(f"Error: File '{csv_filename}' not found.")

    with open(csv_filename, 'r') as file:
        line_number = 0
        player_info = {}
        for line in file:
            split_line = [entry.strip() for entry in line.split(',')]
            if line_number == 0:
                header = split_line
            else:
                if len(split_line) != len(header):
                    raise ValueError(f"Error: Inconsistent number of columns with header: {line}")
                try:
                    player_index = int(split_line[0])
                except ValueError:
                    raise ValueError(f"Error: First column must be player index integers, instead found '{split_line[0]}'")
                player_info[player_index] = split_line
            line_number += 1

        if player1_index not in player_info:
            raise ValueError(f"Error: Player with index {player1_index} not found.")
        
        if player2_index not in player_info:
            raise ValueError(f"Error: Player with index {player2_index} not found.")

        write_player_data(player_info, header, player1_index, 1)
        write_player_data(player_info, header, player2_index, 2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <csv_filename> <player1_number> <player2_number>")
        sys.exit(1)

    try:
        player1_index = int(sys.argv[2])
        player2_index = int(sys.argv[3])
    except ValueError:
        print("Error: Player indexes must be integers.")
        sys.exit(1)

    csv_filename = sys.argv[1]

    parse_player_csv(csv_filename, player1_index, player2_index)
