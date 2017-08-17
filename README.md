# SATMAPS

`SATMAPS` is a python package for obtaning, processing and distributing satellite maps

To install clone the repository: `git clone https://github.com/npolar/satmaps satmaps`, then `cd satmaps && pip install -e .`

To run the software as a standalone application and show help, do `python ./bin/mapmaker.py --help`

To actually make the software search, download, process and send out the results modify the `tmp/sample_request.json` according to your needs and run `python ./bin/mapmaker.py -c credentials.txt -i ../tmp/sample_request.json`, where `credentials.txt` is a two line text file with the username and password for the Copernicus Open Hub.
