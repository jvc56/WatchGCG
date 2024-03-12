import os
from watch_gcg import Game

def get_game_from_gcg(gcg, gcg_line):
    with open(gcg, 'r') as file:
        lines = file.readlines()

    if gcg_line >= len(lines):
        return  # No need to truncate if gcg_line is beyond file length

    tmp_gcg = gcg + str(gcg_line)
    with open(tmp_gcg, 'w') as file:
        file.writelines(lines[:gcg_line])
        file.write(lines[-1])  # Write the last line again to the truncated file
    game = Game(tmp_gcg)
    os.remove(tmp_gcg)
    return game

def assert_watch_gcg_outputs(gcg, gcg_line, p1_score, p2_score, unseen_tiles, unseen_vowels, last_play):
    game = get_game_from_gcg(gcg, gcg_line)
    
    # Assert player scores
    assert game.players.get_score(0) == p1_score
    assert game.players.get_score(1) == p2_score
    
    # Assert unseen tiles
    actual_unseen_tiles, actual_unseen_vowels = game.bag.get_unseen_counts()
    assert actual_unseen_tiles == unseen_tiles
    assert actual_unseen_vowels == unseen_vowels

    # Assert last play
    print(f'vowels: {game.get_last_play_string()}')
    assert game.get_last_play_string() == last_play

def test_watch_gcg():
    assert_watch_gcg_outputs("test.gcg", 4, 68, 0, 86, 36, "!!M!!att...h~`+=-__: 8B EDITION +68 68")
    assert_watch_gcg_outputs("test.gcg", 5, 68, 107, 79, 33, "Josh#%^()&&: A2 POTTIER +107 107")
    assert_watch_gcg_outputs("test.gcg", 6, 68, 0, 86, 36, "Josh#%^()&&: A2 POTTIER +107 107")
    assert_watch_gcg_outputs("test.gcg", 7, 262, 0, 79, 34, "!!M!!att...h~`+=-__: A2 MUZJIKS +194 262")
    assert_watch_gcg_outputs("test.gcg", 8, 262, 170, 72, 30, "Josh#%^()&&: 1A DEUTERA +170 170")
    assert_watch_gcg_outputs("test.gcg", 9, 301, 170, 69, 29, "!!M!!att...h~`+=-__: 1A (DEUTERA)NOM +39 301")
    assert_watch_gcg_outputs("test.gcg", 10, 301, 227, 64, 26, "Josh#%^()&&: 1A (DEUTERANOM)ALIES +57 227")
    assert_watch_gcg_outputs("test.gcg", 11, 384, 227, 57, 23, "!!M!!att...h~`+=-__: O1 (S)POTTIER +83 384")
    assert_watch_gcg_outputs("test.gcg", 12, 384, 323, 50, 20, "Josh#%^()&&: N8 ABBOTCY +96 323")
    assert_watch_gcg_outputs("test.gcg", 14, 391, 543, 41, 16, "Josh#%^()&&: 15H DEXTR(O)SE +220 543")
    assert_watch_gcg_outputs("test.gcg", 17, 465, 603, 30, 11, "Josh#%^()&&: 15H DEXTR(O)SE +220 543")

if __name__ == "__main__":
    test_watch_gcg()