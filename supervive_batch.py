from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
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
team_mappings = {} 




json_key_file = "" # .json API KEY FILE
spreadsheet_name = "Supervive Scrims"
base_team_row = 3  

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
gc = gspread.authorize(creds)
worksheet = gc.open(spreadsheet_name).sheet1


options = webdriver.ChromeOptions()
options.add_argument("--headless") 
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

time.sleep(15)

def process_past_games(num_games):
    """ Processes the past `num_games` custom games in order """
    
    global team_mappings  

    driver.get("https://supervive.op.gg/players/steam-LilMeap%230001")
    time.sleep(5)


    match_containers = driver.find_elements(By.CLASS_NAME, "space-y-2")
    if len(match_containers) < 6:
        print("Could not locate the match history block. Aborting.")
        return

    match_history_block = match_containers[5]  
    past_games = match_history_block.find_elements(By.XPATH, "./div")

    if not past_games:
        print("No games found.")
        return

    print(f"Found {len(past_games)} total games. Processing last {num_games} Custom Games...")

    processed_teams_data = []
    
    team_mappings.clear() 

    for i in range(min(num_games, len(past_games))):
        try:
            game = past_games[i]


            try:
                dropdown_button = game.find_element(By.XPATH, ".//button[contains(@class, 'items-center')]")
                dropdown_button.click()
                print(f"Clicked dropdown for Custom Game #{i+1}.")
                time.sleep(3)  
            except Exception as e:
                print(f"Could not click dropdown for Game {i+1}: {e}")
                continue  


            teams_data = extract_team_data(game)


            if i == 0:
                teams_data = assign_team_names(teams_data)  


            formatted_teams_data = {}
            for team_number, team_info in teams_data.items():
                team_tag = team_mappings.get(team_number, team_number) 
                formatted_teams_data[team_tag] = {"placement": team_info["placement"], "kills": team_info["kills"]}

            processed_teams_data.append(formatted_teams_data)

            print(f"Processed Game #{i+1}")
        
        except Exception as e:
            print(f"Error processing Game #{i+1}: {e}")

    print("Completed batch processing.")
    return processed_teams_data





def open_game_dropdown(game_block):
    """ Click the dropdown to expose team data. """
    while True:
        try:
            dropdown_button = game_block.find_element(
                By.XPATH, ".//button[contains(@class, 'items-center')]"
            )
            dropdown_button.click()
            print("Clicked dropdown.")
            time.sleep(3)  
            break
        except Exception as e:
            print(f"Failed to click dropdown. Retrying... {e}")
            time.sleep(3)

def extract_team_data(latest_game):
    """ Extracts team placements, Team #X, and total kills per team """
    teams_data = {}

    try:

        team_blocks = latest_game.find_elements(
            By.XPATH, ".//div[contains(@class, 'rounded') and contains(@class, 'border-opacity')]"
        )

        print(f"Found {len(team_blocks)} team blocks. Processing...")

        for team in team_blocks:
            try:

                team_number_element = team.find_element(
                    By.XPATH, ".//div[@class='text-muted-foreground']"
                )
                team_number = team_number_element.text.strip()
                print(f"Found {team_number} in team block.")


                try:
                    placement_element = team.find_element(
                        By.XPATH,
                        ".//div[contains(@class, 'flex items-center gap-2')]/div[contains(@class, 'font-bold')]"
                    )
                    placement = placement_element.text.strip()
                    print(f"Placement for {team_number}: {placement}")
                except:
                    placement = "Unknown"
                    print(f"Could not find placement for {team_number}.")


                team_players = []
                try:
                    player_rows = team.find_elements(
                        By.XPATH, ".//div[contains(@class, 'flex items-center justify-between rounded w-full')]"
                    )

                    for row in player_rows:
                        try:

                            player_name_element = row.find_element(
                                By.XPATH, ".//div[contains(@class, 'text-xs cursor-help')]"
                            )
                            player_name = player_name_element.text.strip()
                            team_players.append(player_name)
                            print(f"Found player: {player_name} in {team_number}")
                        except Exception:
                            print("Could not extract player name properly.")

                except Exception as e:
                    print(f"Error extracting player names: {e}")


                total_kills = 0
                try:
                    kill_elements = team.find_elements(
                        By.XPATH,
                        ".//div[contains(@class, 'grid grid-cols-4 gap-1 text-[11px]')]/div[contains(@class, 'flex flex-col items-center w-[50px]')]/div[@class='font-medium']"
                    )

                    for kill_element in kill_elements:
                        kill_text = kill_element.text.strip()
                        if "/" in kill_text:
                            kills = int(kill_text.split("/")[0])
                            total_kills += kills

                except Exception as e:
                    print(f"Error extracting total kills: {e}")

                teams_data[team_number] = {
                    "placement": placement,
                    "kills": total_kills,
                    "players": team_players
                }
                print(f"Stored {team_number}: Placement: {placement}, Kills: {total_kills}, Players: {team_players}")

            except Exception as e:
                print(f"Error processing a team block: {e}")

    except Exception as e:
        print(f"Error extracting team data: {e}")

    return teams_data


def assign_team_names(teams_data):
    """ Assigns correct team names using the majority rule on first detection and persists for future games. """
    global team_mappings

    print("Assigning team names based on player priority rule.")

    for team_number, data in teams_data.items():
        if team_number in team_mappings:

            teams_data[team_number]["team_name"] = team_mappings[team_number]
            print(f"Reused previous mapping: {team_number} → {team_mappings[team_number]}")
            continue


        player_team_counts = {}

        print(f"\nProcessing {team_number}: Players: {data['players']}")

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



def update_spreadsheet(processed_games_data):
    """ Updates Google Sheets with the latest game results using team tags, ensuring Game 1 updates first. """

    print("Performing first batch update for Game 1 (Writing Team Tags and Placements)...")


    first_game_data = processed_games_data[0]  
    placement_column = "B"
    kills_column = "C"

    existing_teams = worksheet.col_values(1) 

    batch_updates = []


    for i, (team_tag, team_info) in enumerate(first_game_data.items()):
        team_row = base_team_row + i  
        batch_updates.append({"range": f"A{team_row}", "values": [[team_tag]]})

        formatted_placement = f"{team_info['placement']} Place"
        batch_updates.append({"range": f"{placement_column}{team_row}", "values": [[formatted_placement]]})
        batch_updates.append({"range": f"{kills_column}{team_row}", "values": [[team_info["kills"]]]})


    worksheet.batch_update(batch_updates)
    print("Game 1 batch update sent.")


    time.sleep(3)


    batch_updates = []  
    for game_index, game_data in enumerate(processed_games_data[1:], start=1):
        placement_column = chr(66 + (game_index * 2))  
        kills_column = chr(67 + (game_index * 2))  

        print(f"Preparing batch update for Game {game_index + 1} → Columns: {placement_column}, {kills_column}")

        existing_teams = worksheet.col_values(1)  

        for team_tag, team_info in game_data.items():
            try:
                if team_tag in existing_teams:
                    team_row = existing_teams.index(team_tag) + 1  
                else:
                    print(f"Could not find {team_tag} in Column A for Game {game_index + 1}. Skipping...")
                    continue

                formatted_placement = f"{team_info['placement']} Place"
                batch_updates.append({"range": f"{placement_column}{team_row}", "values": [[formatted_placement]]})
                batch_updates.append({"range": f"{kills_column}{team_row}", "values": [[team_info["kills"]]]})

            except Exception as e:
                print(f"Error preparing update for {team_tag}: {e}")


    if batch_updates:
        worksheet.batch_update(batch_updates)
        print("Batch update sent for Games 2+.")
    else:
        print("No updates queued for Games 2+.")

    print("Spreadsheet update complete.")




if __name__ == "__main__":
    num_games = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"Processing the past {num_games} Custom Games...")
    processed_games_data = process_past_games(num_games)

    if processed_games_data:
        print("Calling update_spreadsheet() to log data...")
        update_spreadsheet(processed_games_data)
    else:
        print("No valid game data found. Skipping spreadsheet update.")
    print("Completed batch processing.")

