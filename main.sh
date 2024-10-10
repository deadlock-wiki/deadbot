#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi
# Configured completly from env vars:
python3 src/deadbot.py

# example all parameters:
# 
# python3 src/deadbot.py -i $DL_PATH -w $WORKDIR -o $OUTPUT --decompiler_cmd=$DECOMPILER_CMD -dp
#
# or all spelled out:
#
# python3 src/deadbot.py --dl_path $DL_PATH -workdir $WORKDIR -output $OUTPUT --decompiler_cmd=$DECOMPILER_CMD --decompile --parse

# cleanup
if [ "$CLEANUP" = true ]; then
    rm -r $WORKDIR
fi
