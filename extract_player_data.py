import sys
import os

def get_output_filename(column_name, player_number):
    return f"p{player_number}{column_name}.txt"

def write_single_file(column_name, player_number, content):
    with open(get_output_filename(column_name, player_number), 'w') as file:
        file.write(content)

def write_player_data(player_info, header, player_index, player_number):
    player_info_row = player_info[player_index]
    team = ""
    hometown = ""
    for index, column_name in enumerate(header):
        if index == 2:
            team = player_info_row[index]
        if index == 3:
            hometown = player_info_row[index]
        write_single_file(column_name, player_number, player_info_row[index])
    
    write_single_file("preview", player_number, team + "\n" + hometown)


def parse_player_csv(csv_filename, player1_number, player2_number):
    # Check if the CSV file exists
    if not os.path.isfile(csv_filename):
        raise ValueError(f"Error: File '{csv_filename}' not found.")

    with open(csv_filename, 'r') as file:
        line_number = 0
        player_info = {}
        for line in file:
            line = line.strip()
            if line == "":
                continue
            split_line = [entry.strip() for entry in line.split(',')]
            if line_number == 0:
                header = split_line
            else:
                if len(split_line) != len(header):
                    raise ValueError(f"Error: Inconsistent number of columns with header: {line}")
                player_index = split_line[0]
                if player_index != "":
                    player_info[player_index] = split_line
            line_number += 1

        if player1_number not in player_info:
            raise ValueError(f"Error: Player with index {player1_number} not found.")
        
        if player2_number not in player_info:
            raise ValueError(f"Error: Player with index {player2_number} not found.")

        write_player_data(player_info, header, player1_number, 1)
        write_player_data(player_info, header, player2_number, 2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <csv_filename> <player1_number> <player2_number>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    player1_index = sys.argv[2]
    player2_index = sys.argv[3]

    parse_player_csv(csv_filename, player1_index, player2_index)
