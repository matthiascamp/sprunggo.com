#!/bin/zsh
cd -- "${0:A:h}"
print 'Sprung Go local copy: http://127.0.0.1:8000'
print 'Press Control-C to stop the server.'
open http://127.0.0.1:8000
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
