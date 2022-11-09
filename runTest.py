from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import sys

URL = ""

STREAM_TIMEOUT_SEC = 900 # Timeout streams after 15 minutes and assume it encountered errors.

URL_CONFIRM_BUTTON_ID = "urlConfirmButton"
STREAM_DONE_LABEL_ID = "streamDoneLabel"
SAVE_BUTTON_ID = "save_btn"

def main():
    url = URL
    if (len(sys.argv) > 1):
        url = sys.argv[1] # URL should be the first element in the input.
    print("Received URL: " + url)

    options = Options()
    print("Options created")
    options.add_argument("-headless")
    print("Options set. Launching browser")
    ffDriver = webdriver.Firefox(options = options)
    print("Browser launched")

    pathToIndex = os.path.join(os.getcwd(), "index.html")
    
    print("Navigating browser to " + pathToIndex)
    ffDriver.get(pathToIndex)

    print(ffDriver.title)

    # Enter the URL for the manifest to be streamed in the input field.
    web_urlInput = ffDriver.find_element(By.ID, "urlInput")
    web_urlInput.send_keys(URL)

    # Start the stream.
    web_urlConfirmButton = ffDriver.find_element(By.ID, URL_CONFIRM_BUTTON_ID)
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

    ffDriver.quit()

if __name__ == "__main__":
    main()