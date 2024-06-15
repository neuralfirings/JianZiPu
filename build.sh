#!/bin/bash
cp ./src/JianZiPu.otf ./dist/JianZiPu.otf
uglifyjs ./src/*.js -o ./dist/jianzipu.min.js
