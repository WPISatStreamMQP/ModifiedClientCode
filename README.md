# WPI Satellite MQP Test Scripts

This repository contains the majority of our code and work for running satellite video stream tests and analyzing the results.

## Running this script on Glomma.

This script has already been installed on Glomma, and we try to keep that version up-to-date with the `main` branch here. Here is how to run the single-run test script (`runTest.py`) on Glomma:

* Log in
* `> cd /var/PyTestScript`
* `> source /var/PyTestScript/testVenv/bin/activate`. This activates the Python 3.10 virtual environment that has all of the Python packages needed for the script.
* Your command line prompt should now start with `(testVenv)`, indicating that the virtual environment is running. If you need to disable it, run `deactivate`.
* `> python ./runTest.py [url to manifest file] [name of interface to capture packets from]` For example, set the URL to `http://mlcneta.cs.wpi.edu/manifest_20000ms.mpd` and the interface to `eno2` to test from MLCNetA over the satellite link.
* The script will start running, and will produce outputs in the command-line as it runs. It could take a while to run, but you can just leave it running without watching! It will automatically terminate and return to the command-line when it's done.
  * The Big Buck Bunny video is about 10.5 minutes long, so the script will take at least that amount of time to complete. Generally, expect it to complete within 15 minutes. There is an automatic timeout where if the stream takes more than 30 minutes (by default) to complete, the script will automatically stop it and save the data. To change this timeout setting, change the `STREAM_TIMEOUT_SEC` constant value at the top of `runTest.py`.
* There should be a new directory in `/var/PyTestScript` that has a name something like this `Results_[timestamp]_[hostname, should be "glomma"]`. The output from the script will also show you the name of this directory. The test script log, the .pcap file, and the packet .csv file should all be in there.