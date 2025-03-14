from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
import re
import sys

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors="replace")



TEAM_FILE = "teams.json"

def load_teams():
    try:
        with open(TEAM_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


teams = load_teams()


json_key_file = "supervive-scrims-c69705ffbf52.json"
spreadsheet_name = "Supervive Scrims"
base_team_row = 3  # start at row 3

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
gc = gspread.authorize(creds)
worksheet = gc.open(spreadsheet_name).sheet1


options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


placement_mapping = {
    "1st": "1st Place",
    "2nd": "2nd Place",
    "3rd": "3rd Place",
    "4th": "4th Place",
    "5th": "5th Place",
    "6th": "6th Place",
    "7th": "7th Place",
    "8th": "8th Place",
    "9th": "9th Place",
    "10th": "10th Place",
}


team_index = 0 # track enabled teams

for team_name, team_data in teams.items():
    if not team_data.get("enabled", True):  # skip disabled teams
        print(f"> Skipping disabled team: {team_name}", flush=True)
        continue

    players = team_data["players"]
    team_row = base_team_row + team_index
    team_data = {
        "Placement": [],
        "Kills": [0] * 5
    }

    placement_player = players[0] 

    print(f"\n---> Processing team: {team_name} ({team_row})", flush=True)
    time.sleep(10)
    for player_url in players:
        driver.get(player_url)
        time.sleep(0.5)

        # refresh match history
        try:
            fetch_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Fetch New Matches')]"))
            )
            fetch_button.click()
            time.sleep(0.5)
            driver.refresh()
            time.sleep(0.5)
            print(f"-> Refreshed match history for {player_url}", flush=True)
        except Exception:
            print(f" 'Fetch New Matches' button not found or already updated for {player_url}", flush=True)

        # locate match history container
        try:
            match_sections = driver.find_elements(By.CLASS_NAME, "space-y-2")

            match_section = None
            for section in match_sections:
                if "KDA Trend" not in section.text and "Placement Trend" not in section.text:
                    match_section = section
                    break

            if not match_section:
                print(f" No valid match history found for {player_url}", flush=True)
                continue
        except Exception as e:
            print(f" Error loading match history for {player_url}: {e}", flush=True)
            continue

        matches = match_section.find_elements(By.XPATH, ".//div[contains(@class, 'flex') and contains(@class, 'items-center') and contains(@class, 'justify-between') and contains(@class, 'border')]")

        # filter for custom matches
        custom_games = []
        for match in matches:
            try:
                match_type_element = match.find_element(By.XPATH, ".//div[contains(@class, 'text-xs') and contains(@class, 'font-bold') and contains(@class, 'text-red-500')]")
                match_type = match_type_element.text.strip()
                if match_type == "Custom Game":
                    custom_games.append(match)
            except Exception:
                continue 

        if len(custom_games) < 5:
            print(f" Only {len(custom_games)} 'Custom Game' matches found, adjusting to available matches.", flush=True)

        for i, match in enumerate(custom_games[:5]): 
            try:
                # extract placement
                if player_url == placement_player:
                    try:
                        placement_element = match.find_element(By.XPATH, ".//div[contains(@class, 'text-sm') and contains(@class, 'text-muted-foreground')]")
                        placement = placement_element.text.strip().split(" ")[0] 
                        placement = placement_mapping.get(placement, "Unknown")
                    except Exception:
                        placement = "Unknown"

                    if len(team_data["Placement"]) < i + 1:
                        team_data["Placement"].append(placement)

                # extract kills
                try:
                    kda_element = match.find_element(By.XPATH, ".//div[contains(@class, 'text-sm') and contains(text(), '/')]")
                    kda_text = kda_element.text.strip().split(" / ")
                    kills = int(kda_text[0])
                except Exception:
                    kills = 0

                team_data["Kills"][i] += kills 

            except Exception as e:
                print(f" Error extracting match data for {player_url}: {e}", flush=True)

    # fill missing matches
    while len(team_data["Placement"]) < 5:
        team_data["Placement"].append("Missing")

    # write to sheets
    team_column = "A"
    placement_column_start = "B"
    kill_column_start = "C"

    worksheet.update(f"{team_column}{team_row}", [[team_name]])

    for i in range(5):
        placement_cell = f"{chr(ord(placement_column_start) + i * 2)}{team_row}"
        kill_cell = f"{chr(ord(kill_column_start) + i * 2)}{team_row}"
        worksheet.update(placement_cell, [[team_data["Placement"][i]]])
        worksheet.update(kill_cell, [[team_data["Kills"][i]]])

    print(f"---> Data written for team: {team_name}", flush=True)

    team_index += 1

driver.quit()
