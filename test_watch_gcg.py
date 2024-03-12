import os
from watch_gcg import Game

def get_game_from_gcg(gcg, gcg_line):
    with open(gcg, 'r') as file:
        lines = file.readlines()

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
    assert game.get_last_play_string() == last_play

def test_watch_gcg():
    assert_watch_gcg_outputs("test.gcg", 4, 68, 0, 86, 37, "!!M!!att...h~`+=-__: 8B EDITION +68 68")
    assert_watch_gcg_outputs("test.gcg", 5, 68, 107, 79, 34, "Josh#%^()&&: A2 POTTIER +107 107")
    assert_watch_gcg_outputs("test.gcg", 6, 68, 0, 86, 37, "Josh#%^()&&: A2 POTTIER +107 107")
    assert_watch_gcg_outputs("test.gcg", 7, 262, 0, 79, 35, "!!M!!att...h~`+=-__: A2 MUZJIKS +194 262")
    assert_watch_gcg_outputs("test.gcg", 8, 262, 170, 72, 31, "Josh#%^()&&: 1A DEUTERA +170 170")
    assert_watch_gcg_outputs("test.gcg", 9, 301, 170, 69, 30, "!!M!!att...h~`+=-__: 1A (DEUTERA)NOM +39 301")
    assert_watch_gcg_outputs("test.gcg", 10, 301, 227, 64, 27, "Josh#%^()&&: 1A (DEUTERANOM)ALIES +57 227")
    assert_watch_gcg_outputs("test.gcg", 11, 384, 227, 57, 24, "!!M!!att...h~`+=-__: O1 (S)POTTIER +83 384")
    assert_watch_gcg_outputs("test.gcg", 12, 384, 323, 50, 21, "Josh#%^()&&: N8 ABBOTCY +96 323")
    assert_watch_gcg_outputs("test.gcg", 14, 391, 543, 41, 17, "Josh#%^()&&: 15H DEXTR(O)SE +220 543")
    assert_watch_gcg_outputs("test.gcg", 17, 465, 603, 30, 12, "!!M!!att...h~`+=-__: pass +0 465")
    assert_watch_gcg_outputs("test.gcg", 18, 465, 603, 30, 12, "Josh#%^()&&: pass +0 603")
    assert_watch_gcg_outputs("test.gcg", 19, 465, 603, 30, 12, "!!M!!att...h~`+=-__: pass +0 465")
    assert_watch_gcg_outputs("test.gcg", 20, 465, 603, 30, 12, "Josh#%^()&&: exch HGRV +0 603")
    assert_watch_gcg_outputs("test.gcg", 21, 465, 603, 30, 12, "!!M!!att...h~`+=-__: exch EEEOW +0 465")
    assert_watch_gcg_outputs("test.gcg", 28, 516, 807, 9, 4, "Josh#%^()&&: 12A (Y)E(F)G(S)I(CH)I(L)RWz(TG) +170 807")
    assert_watch_gcg_outputs("test.gcg", 31, 516, 833, 4, 2, "Josh#%^()&&: 5A (J)EaNED +26 833")

if __name__ == "__main__":
    test_watch_gcg()