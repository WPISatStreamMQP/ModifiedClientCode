from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import sys
import datetime
import socket

STREAM_TIMEOUT_SEC = 900 # Timeout streams after 15 minutes and assume it encountered errors.
GENERIC_TIMEOUT_SEC = 3 # When accessing a regular element, timeout after just three seconds.

URL_INPUT_FIELD_ID = "urlInput"
URL_CONFIRM_BUTTON_ID = "urlConfirmButton"
STREAM_DONE_LABEL_ID = "streamDoneLabel"
SAVE_BUTTON_ID = "save_btn"

def main():
    # TODO: Log any settings at the beginning of running this script. EG the timeout setting, the URL, etc.

    if (len(sys.argv) < 2):
        print("No URL argument received")
    url = sys.argv[1] # URL should be the first element in the input.
    print("Received URL: " + url)

    options = Options()
    print("Options created")
    #options.add_argument("-headless")
    #options.add_argument("-P")
    #options.add_argument("headlessTester")
    print("Options set. Launching browser")
    ffDriver = webdriver.Firefox(options = options)
    print("Browser launched")

    pathToIndex = os.path.join(os.getcwd(), "index.html")
    
    print("Navigating browser to " + pathToIndex)
    ffDriver.get(pathToIndex)

    print(ffDriver.title)

    # Enter the URL for the manifest to be streamed in the input field.
    print("Inputting URL to webpage.")
    web_urlInput = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_INPUT_FIELD_ID)))
    web_urlInput.clear()
    web_urlInput.send_keys(url)

    # Start the stream.
    print("Starting stream.")
    web_urlConfirmButton = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, URL_CONFIRM_BUTTON_ID)))
    web_urlConfirmButton.click()

    try:
        web_doneLabel = WebDriverWait(ffDriver, STREAM_TIMEOUT_SEC).until(EC.visibility_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
        # Successfully loaded the done label, so the stream finished. This means the log will have been saved by the JS script.
        print("Stream completed.")
    except TimeoutException:
        print("Timeout limit reached before stream completed.")
        # Since the stream failed to finish, it has not saved the log. Do that for it.
        web_saveButton = ffDriver.find_element(By.ID, SAVE_BUTTON_ID)
        web_saveButton.click()

    # Make a directory for this run of the test.
    workingDirectory = os.getcwd()
    now_iso = datetime.datetime.now().isoformat().replace(":", "_") # Replace colons with underscores because Windows is evil.
    myHostname = socket.gethostname()
    resultsDirName = "Results_" + now_iso + "_" + myHostname
    resultsDirPath = os.path.join(workingDirectory, resultsDirName)
    os.mkdir(resultsDirPath)
    print("Results will be saved in directory " + resultsDirPath)

    web_doneLabel = WebDriverWait(ffDriver, GENERIC_TIMEOUT_SEC).until(EC.presence_of_element_located((By.ID, STREAM_DONE_LABEL_ID)))
    # After the save button is clicked, the done label will be filled with the title of the saved file.
    logName = web_doneLabel.get_attribute("textContent")
    downloadsPath = os.path.join(os.path.expanduser("~"), "Downloads") # This works on both Linux and Windows, assuming the downloads folder is the default.
    # Still have to search for the most recent file that contains the name because the JS player doesn't know if it was downloaded with a duplicate identifier (like `(1)`, `(2)`, etc) appended.
    mostRecentFileName = getLatestFileContainsNamePath(downloadsPath, logName)
    if (mostRecentFileName == ""):
        print("No JavaScript log file located. File will not be moved.")
    else:
        mostRecentFilePath = os.path.join(downloadsPath, mostRecentFileName)

        # Move the data files to the new directory.
        movedLogFilePath = os.path.join(resultsDirPath, mostRecentFileName)
        os.rename(mostRecentFilePath, movedLogFilePath)
        print("JavaScript log data moved to " + movedLogFilePath)

    print("Exiting browser")
    ffDriver.quit()
    print("Test completed. Exiting")

def getLatestFileContainsNamePath(dirPath, name):
    #files = sorted((f for f in os.listdir(dirPath) if f.find(name) != -1), 
    #               key=lambda f: os.stat(os.path.join(dirPath, f)).st_mtime)
    files = sorted((f for f in os.listdir(dirPath) if f.find(name) != -1), 
                   key=lambda f: os.path.getmtime(os.path.join(dirPath, f)))
    if (len(files) == 0):
        # There were no files located.
        return ""
    mostRecent = files[-1]
    return mostRecent

if __name__ == "__main__":
    main()