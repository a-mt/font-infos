
List the character map, metadatas and features of a given font.  
Inspiration: http://torinak.com/font/lsfont.html

## Install

Install [ttf2woff](https://github.com/doio/ttf2woff)

    # Place yourself in the project directory
    cd font-infos

    # Download & install ttf2woff (OTF/TTF to WOFF converter)
    wget http://wizard.ae.krakow.pl/%7Ejb/ttf2woff/ttf2woff-1.2.tar.gz
    tar xzf ttf2woff-1.2.tar.gz
    rm !$
    cd ttf2woff-1.2
    make

Install [fonttools](https://github.com/fonttools/fonttools)

    pip install fonttools
    pip install brotli # to handle WOFF2

Install [web.py](https://github.com/webpy/webpy)

    pip install web.py

## Run

    python bin/app.py

### "No socket could be created" Error

If a connection on port 80 is already open, an error is thrown

    File "/usr/local/lib/python2.7/dist-packages/web/wsgiserver/__init__.py", line 1753, in start
      raise socket.error(msg)

To list active Internet connections:

    netstat -tulpn

To stop it:

    kill <PID>