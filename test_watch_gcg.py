import os
from watch_gcg import Game, read_definitions

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

def assert_watch_gcg_outputs(gcg, word_definitions, gcg_line, p1_score, p2_score, unseen_tiles, unseen_vowels, last_play):
    game = get_game_from_gcg(gcg, gcg_line)
    
    # Assert player scores
    assert game.players.get_score(0) == p1_score
    assert game.players.get_score(1) == p2_score
    
    # Assert unseen tiles
    actual_unseen_tiles, actual_unseen_vowels = game.bag.get_unseen_counts()
    assert actual_unseen_tiles == unseen_tiles
    assert actual_unseen_vowels == unseen_vowels

    # Assert last play
    assert game.get_last_play_string(word_definitions) == last_play

def test_watch_gcg():
    word_definitions = read_definitions("NWL23defs.csv")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 3, 0, 0, 93, 41, "")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 4, 68, 0, 86, 37, "     LAST PLAY: !!M!!att...h~`+=-__ 8B EDITION +68 68 | a particular series of printed material [n EDITIONS]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 5, 68, 107, 79, 34, "     LAST PLAY: Josh#%^()&& A2 POTTIER +107 107 | from POTTY (of little importance : POTTINESS / a small toilet seat) [adj]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 6, 68, 0, 86, 37, "     LAST PLAY: Josh#%^()&& A2 POTTIER +107 107 | from POTTY (of little importance : POTTINESS / a small toilet seat) [adj]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 7, 262, 0, 79, 35, "     LAST PLAY: !!M!!att...h~`+=-__ A2 MUZJIKS +194 262 | from MUZJIK (muzhik) [n]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 8, 262, 170, 72, 31, "     LAST PLAY: Josh#%^()&& 1A DEUTERA +170 170 | ")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 9, 301, 170, 69, 30, "     LAST PLAY: !!M!!att...h~`+=-__ 1A (DEUTERA)NOM +39 301 | ")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 10, 301, 227, 64, 27, "     LAST PLAY: Josh#%^()&& 1A (DEUTERANOM)ALIES +57 227 | from DEUTERANOMALY (partial loss of green color vision) [n]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 11, 384, 227, 57, 24, "     LAST PLAY: !!M!!att...h~`+=-__ O1 (S)POTTIER +83 384 | from SPOTTY (marked with spots : SPOTTILY, SPOTTINESS) [adj]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 12, 384, 323, 50, 21, "     LAST PLAY: Josh#%^()&& N8 ABBOTCY +96 323 | the office of an abbot [n ABBOTCIES]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 14, 391, 543, 41, 17, "     LAST PLAY: Josh#%^()&& 15H DEXTR(O)SE +220 543 | a form of glucose [n DEXTROSES]")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 17, 465, 603, 30, 12, "     LAST PLAY: !!M!!att...h~`+=-__ pass +0 465")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 18, 465, 603, 30, 12, "     LAST PLAY: Josh#%^()&& pass +0 603")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 19, 465, 603, 30, 12, "     LAST PLAY: !!M!!att...h~`+=-__ pass +0 465")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 20, 465, 603, 30, 12, "     LAST PLAY: Josh#%^()&& exch HGRV +0 603")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 21, 465, 603, 30, 12, "     LAST PLAY: !!M!!att...h~`+=-__ exch EEEOW +0 465")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 28, 516, 807, 9, 4, "     LAST PLAY: Josh#%^()&& 12A (Y)E(F)G(S)I(CH)I(L)RWz(TG) +170 807 | ")
    assert_watch_gcg_outputs("test.gcg", word_definitions, 31, 516, 833, 4, 2, "     LAST PLAY: Josh#%^()&& 5A (J)EaNED +26 833 | wearing jeans [adj]")

if __name__ == "__main__":
    test_watch_gcg()