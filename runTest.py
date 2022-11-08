from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import os

def main():
    options = Options()
    print("Options created")
    #options.headless = True
    options.add_argument("-headless")
    #options.add_argument("-P")
    #options.add_argument("headlessTester")
    print("Options set")
    ffDriver = webdriver.Firefox(options = options)
    print("Browser launched")

    pathToIndex = os.path.join(os.getcwd(), "index.html")
    
    print("Navigating browser to " + pathToIndex)
    ffDriver.get(pathToIndex)

    print(ffDriver.title)

    ffDriver.quit()

if __name__ == "__main__":
    main()