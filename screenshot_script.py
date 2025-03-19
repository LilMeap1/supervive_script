from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from PIL import Image
import time
import subprocess


SPREADSHEET_URL = "" # SPREADSHEET URL GOES HERE


options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")  
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


driver.get(SPREADSHEET_URL)
time.sleep(5)  


table_element = driver.find_element(By.XPATH, "//div[contains(@class, 'grid-container')]") 


full_screenshot_path = "full_spreadsheet.png"
driver.save_screenshot(full_screenshot_path)


location = table_element.location
size = table_element.size
x, y = location["x"], location["y"]
width, height = size["width"], size["height"]


crop_x_left = x + 52  
crop_y_top = y + 25  
crop_x_right = x + width - 255  
crop_y_bottom = y + height - 127  


image = Image.open(full_screenshot_path)
cropped_image = image.crop((crop_x_left, crop_y_top, crop_x_right, crop_y_bottom))


cropped_screenshot_path = "/tmp/spreadsheet_final.png"
cropped_image.save(cropped_screenshot_path)
print(f"Final Cropped Screenshot saved as {cropped_screenshot_path}")

subprocess.run(["python", "discord_bot.py"]) 


driver.quit()
