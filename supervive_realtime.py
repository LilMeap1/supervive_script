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
import sys
import re
import hashlib


sys.stdout.reconfigure(encoding='utf-8')  

TEAM_FILE = "teams.json"

def load_teams():
    try:
        with open(TEAM_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Warning: Could not load teams.json. Using empty fallback.")
        return {}  

teams = load_teams()  


json_key_file = "" # .json API KEY FILE HERE
spreadsheet_name = "Supervive Scrims"
base_team_row = 3  

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
gc = gspread.authorize(creds)
worksheet = gc.open(spreadsheet_name).sheet1


options = webdriver.ChromeOptions()
options.add_argument("--headless")  
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


team_mappings = {}
processed_games = 0  

time.sleep(15)

processed_games = set()  

def fetch_new_games():
    fetch_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Fetch New Matches')]")
    fetch_button.click()
    print("Clicked 'Fetch New Matches' to refresh data.")
    time.sleep(5)  

def generate_game_key(game_text):
    """Generate a unique key for the game based on its details, excluding timestamps."""

    cleaned_text = re.sub(r"(\d+\s+minutes\s+ago|\d+\s+hours\s+ago|an hour ago|\d+\s+days\s+ago)", "", game_text, flags=re.IGNORECASE)
    

    game_hash = hashlib.md5(cleaned_text.encode()).hexdigest()
    return game_hash

def fetch_latest_custom_game():
    """ Find the latest completed Custom Game and open it. """
    first_attempt = True  

    while True:
        driver.get("https://supervive.op.gg/players/steam-LilMeap%230001") # OP.GG of user in the games
        time.sleep(5)


        if first_attempt:
            try:
                fetch_new_games()
            except:
                print("'Fetch New Matches' button not found on first attempt.")

            first_attempt = False  

        try:
            match_containers = driver.find_elements(By.CLASS_NAME, "space-y-2")
            if len(match_containers) < 6:
                print("Could not locate the correct match history block. Retrying...")
                time.sleep(15)
                continue

            match_history_block = match_containers[5]  
            past_games = match_history_block.find_elements(By.XPATH, "./div")  

            if not past_games:
                print("No games found. Retrying...")
                time.sleep(15)
                continue

            print(f"Found {len(past_games)} possible game blocks. Checking first Custom Game...")

            latest_game = None
            
            first_game = past_games[0]

            try:
                
                custom_game_label = first_game.find_elements(By.XPATH, ".//div[contains(@class, 'text-xs font-bold text-red-500')]")
                
                if custom_game_label and "Custom Game" in custom_game_label[0].text:
                    print(f"Found latest Custom Game at position 1.")

                   
                    time_label_element = first_game.find_element(By.XPATH, ".//div[contains(@class, 'text-muted-foreground')]")
                    time_label = time_label_element.text.strip().lower()
                    print(f"Game time label: {time_label}")


                    if "minute" in time_label:  
                        match = re.search(r"(\d+)", time_label)  
                        if match:
                            minutes_ago = int(match.group(1))
                            if minutes_ago > 5:
                                print("Game is older than 5 minutes. Fetching new matches.")
                                try:
                                    fetch_new_games()
                                    continue  
                                except:
                                    print("'Fetch New Matches' button not found.")
                                time.sleep(30)
                                continue  
                    elif "hour" in time_label or "day" in time_label:  
                        print("Game is too old. Skipping & waiting for a new match.")
                        fetch_new_games()
                        continue  


                    game_text = first_game.text.strip()
                    if game_text in processed_games:
                        print("Same game found. Clicking 'Fetch New Matches' and retrying...")
                        try:
                            fetch_new_games()
                        except:
                            print("'Fetch New Matches' button not found.")


                        time.sleep(30)  
                        continue  

                    latest_game = first_game  

            except:
                print("Error checking first game. Retrying...")
                time.sleep(30)
                continue  

            if not latest_game:
                print("No recent Custom Game found. Waiting...")
                time.sleep(30)
                continue  


            while True:
                try:
                    dropdown_button = latest_game.find_element(By.XPATH, ".//button[contains(@class, 'items-center')]")
                    dropdown_button.click()
                    print("Clicked dropdown via button.")
                    time.sleep(3) 
                    break  
                except Exception as e:
                    print(f"Failed to click dropdown, game might be in progress. Retrying in 30s... {e}")
                    time.sleep(30)  

            return latest_game  

        except Exception as e:
            print(f"Error finding Custom Game: {e}. Retrying...")
            time.sleep(15)


def extract_team_data(latest_game):
    """ Extracts team placements, Team #X, and kill counts """
    teams_data = {}
    try:

        team_blocks = latest_game.find_elements(By.XPATH, ".//div[contains(@class, 'rounded') and contains(@class, 'border-opacity')]")


        print(f"Found {len(team_blocks)} team blocks. Processing...")

        for team in team_blocks:
            try:

                team_number_element = team.find_element(By.XPATH, ".//div[@class='text-muted-foreground']")
                team_number = team_number_element.text.strip()
                print(f"Found {team_number} in team block.")


                try:
                    placement_element = team.find_element(By.XPATH, ".//div[contains(@class, 'flex items-center gap-2')]/div[contains(@class, 'font-bold')]")
                    placement = placement_element.text.strip()
                    print(f"Placement for {team_number}: {placement}")
                except:
                    placement = "Unknown"
                    print(f"Could not find placement for {team_number}.")


                players = team.find_elements(By.XPATH, ".//div[contains(@class, 'cursor-help')]")
                total_kills = 0
                team_players = []

                for player in players:
                    player_name = player.text.strip()
                    team_players.append(player_name)
                    print(f"Found player: {player_name} in {team_number}")

                try:

                    player_rows = team.find_elements(By.XPATH, ".//div[contains(@class, 'flex items-center justify-between rounded w-full')]")
                    num_players = len(player_rows)


                    kill_values = []
                    try:

                        kda_blocks = team.find_elements(By.XPATH, ".//div[contains(@class, 'grid grid-cols-4 gap-1 text-[11px]')]/div[contains(@class, 'flex flex-col items-center w-[50px]')]/div[@class='font-medium']")
                        
                        for kda in kda_blocks:
                            kda_text = kda.text.strip()
                            if "/" in kda_text:  
                                kills = int(kda_text.split('/')[0])  
                                kill_values.append(kills)

                        if len(kill_values) != num_players:
                            print(f"Data mismatch: Players ({num_players}) != KDA values ({len(kill_values)})")
                        else:
                            print(f"Extracted kills: {kill_values}")

                    except Exception as e:
                        print(f"Error extracting kills list: {e}")


                    for i, player_row in enumerate(player_rows):
                        try:
                            player_name = player_row.find_element(By.XPATH, ".//a").text.strip()  

                            if i < len(kill_values):  
                                kills = kill_values[i]
                                total_kills += kills
                                
                            else:
                                print(f"Could not find kills for {player_name}")

                        except Exception:
                            print(f"Could not extract player data properly.")
                except Exception as e:
                    print(f"Error extracting kills: {e}")





                teams_data[team_number] = {"placement": placement, "kills": total_kills, "players": team_players}
                print(f"Stored {team_number}: Placement: {placement}, Kills: {total_kills}, Players: {team_players}")

            except Exception as e:
                print(f"Error processing a team block: {e}")

    except Exception as e:
        print(f"Error extracting team data: {e}")

    return teams_data



team_mappings = {} 
games_since_reset = 0  

def assign_team_names(teams_data):
    """ Assigns correct team names using the majority rule on first detection and persists for 5 games. """
    global team_mappings, games_since_reset


    if games_since_reset >= 5:
        print("Resetting team mappings. New series detected.")
        team_mappings.clear()
        games_since_reset = 0

    for team_number, data in teams_data.items():
        if team_number in team_mappings:

            teams_data[team_number]["team_name"] = team_mappings[team_number]
            print(f"Reused previous mapping: {team_number} → {team_mappings[team_number]}")
            continue


        player_team_counts = {}

        print(f"\nProcessing {team_number}: {data['players']}")

        for team_name, team_info in teams.items():
            for player in data["players"]:
                if player in team_info["players"]:
                    if team_name not in player_team_counts:
                        player_team_counts[team_name] = 0
                    if player == team_info["captain"]:
                        player_team_counts[team_name] += 3  
                        print(f"{player} is a Captain of {team_name} (+3 points)")
                    else:
                        player_team_counts[team_name] += 2  
                        print(f"{player} is a Member of {team_name} (+2 points)")

        if player_team_counts:
            best_team = max(player_team_counts, key=player_team_counts.get)
            print(f"Assigned {team_number} to {best_team} with {player_team_counts[best_team]} points")
            team_mappings[team_number] = best_team
            teams_data[team_number]["team_name"] = best_team

    return teams_data


def format_placement(placement):
    """ Format placement to match dropdown values in the spreadsheet (1st - 10th). """
    try:
        num = int(placement)  
        if num < 1: 
            return "10th Place"  


        num = min(num, 10)

        suffix = {1: "st", 2: "nd", 3: "rd"}.get(num, "th")
        return f"{num}{suffix} Place"
    
    except ValueError:
        return "10th Place"  


def update_spreadsheet(teams_data):
    """ Updates Google Sheets with the latest game results. """
    global games_since_reset


    game_index = games_since_reset  
    placement_column = chr(66 + (game_index * 2))  
    kills_column = chr(67 + (game_index * 2))  
    print(f"Updating spreadsheet for Game {game_index + 1} → Columns: {placement_column}, {kills_column}")


    existing_teams = worksheet.col_values(1)  

    for team_number, team_data in teams_data.items():
        try:

            if team_number in team_mappings:
                team_tag = team_mappings[team_number]
            else:
                print(f"No mapping found for {team_number}, using fallback.")
                team_tag = team_number  


            if games_since_reset == 0:

                team_row = base_team_row + list(teams_data.keys()).index(team_number)
                worksheet.update(f"A{team_row}", [[team_tag]])
            else:

                if team_tag in existing_teams:
                    team_row = existing_teams.index(team_tag) + 1  
                else:
                    print(f"Could not find {team_tag} in Column A. Skipping...")
                    continue


            formatted_placement = f"{team_data['placement']} Place"  
            worksheet.update(f"{placement_column}{team_row}", [[formatted_placement]])
            worksheet.update(f"{kills_column}{team_row}", [[team_data["kills"]]])

            print(f"Updated {team_tag} → Placement: {formatted_placement}, Kills: {team_data['kills']}")

        except Exception as e:
            print(f"Error updating {team_tag}: {e}")

    games_since_reset += 1 


while True:
    latest_game = fetch_latest_custom_game()
    teams_data = extract_team_data(latest_game)
    teams_data = assign_team_names(teams_data)
    update_spreadsheet(teams_data)
    print("Game processed. Waiting for next game...")
    time.sleep(60)
