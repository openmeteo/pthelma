export PYTHONPATH = ./lib

DBHOST = acheloos
DBNAME = hydria
DBUSER = hydro
DBPASSWD = foufotos

default:
	false

clean:
	rm -f lib/*.pyc

test:
	tests/test_timeseries.py $(DBHOST) $(DBNAME) $(DBUSER) $(DBPASSWD)
	tests/test_meteologger.py $(DBHOST) $(DBNAME) $(DBUSER) $(DBPASSWD)
