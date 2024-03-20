# WatchGCG

This repo contains scripts to extract game data from GCG files in realtime for live stream broadcasts. Right now it only contains the watch_gcg.py script, but we might add more later.

## Using watch_gcg.py to capture realtime output from a GCG file

The watch_gcg.py script requires that you have python3 installed on your computer. You can follow the steps [here](https://kinsta.com/knowledgebase/install-python) to install python3 for your operating system.

Once python3 is installed, you will need to install the python watchfiles module. This module allows python to "watch" the GCG file you are editing so it can update the output files when it detects the GCG file has changed. Install the module with the following command:

```
python -m pip install watchfiles
```

Alternatively, your python command might be called 'python3' in which case you would need to run the following command:

```
python3 -m pip install watchfiles
```

Once the watchfiles module is installed, you can now run the watch_gcg.py script. The script needs 5 arguments:

- The input GCG file to watch
- The input lexicon file with definitions
- The output file name for the scores
- The output file name for the unseen tiles
- The output file name for the unseen tiles count
- The output file name for the last play
- The output file name for the last play definition

For example, to watch a GCG file called 'alice_vs_bob.gcg', use the following command:

```
python3 watch_gcg.py --gcg alice_vs_bob.gcg --lex CSW21_with_defs.txt --score score.txt --unseen unseen.txt --count count.txt --lp lp.txt --dfn def.txt
```

The script should now run indefinitely watching for changes to the GCG file. To stop execution, hit control-C.

The output files will update whenever the GCG file changes, so if you are editing the GCG file in Quackle, it will not write to the output files until you save the game in Quackle.
