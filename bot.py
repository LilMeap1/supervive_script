import discord
import threading
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from flask import Flask
import subprocess
from threading import Thread
import json
import psutil
import time

# THIS BOT IS RUNNING IN REPLIT FOR SEMI 24/7 UP-TIME

TOKEN = ""  # Discord Bot Token
GUILD_ID = ""  # Discord Server ID
app = Flask(__name__)


@app.route('/')
def home():
  return "Bot is alive!"


def run():
  app.run(host="0.0.0.0", port=8080)


IMAGE_PATH = "/tmp/spreadsheet_final.png"


threading.Thread(target=run, daemon=True).start()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


ALLOWED_ROLES = {"New Tech", "Admin", "Owner", "Helper guy"}


REALTIME_SCRIPT = "supervive_realtime.py"
BATCH_SCRIPT = "supervive_batch.py"
TEAMS_JSON = "teams.json"

SCRIMS_COMMANDS = {
    "/scrims_start_realtime": "Starts real-time calculations.",
    "/scrims_stop": "Stops the calculations.",
    "/results": "Sends results (screenshot of spreadsheet).",
    "/scrims_calc_past <number>": "Calculates past <number> custom games.",
    "/team_add <TAG> <Captain> <Member1> <Member2> <Member3> <Captain's-op.gg>":
    "Adds a team with specified members.",
    "/team_remove <TAG>": "Removes a team by its tag."
}



def has_permission(interaction: discord.Interaction):
  if not isinstance(interaction.user,
                    discord.Member): 
    return False

  return any(role.name in ALLOWED_ROLES for role in interaction.user.roles)


def stop_script(script_name):
  for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
      if script_name in " ".join(
          proc.info['cmdline']):  
        proc.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      continue
  return False



@bot.tree.command(name="help_scrims",
                  description="Shows all available scrims-related commands.")
async def help_scrims(interaction: discord.Interaction):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  embed = discord.Embed(
      title="📌 Scrims Commands Help",
      description="Here are all the available scrims-related commands:",
      color=discord.Color.blue())

  for command, description in SCRIMS_COMMANDS.items():
    embed.add_field(name=command, value=description, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="scrims_start_realtime",
                  description="Starts real-time calculations")
async def scrims_start_realtime(interaction: discord.Interaction):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  subprocess.Popen(["python", REALTIME_SCRIPT])
  await interaction.response.send_message("Real-time calculations started!")



@bot.tree.command(name="scrims_stop", description="Stops the calculations")
async def scrims_stop(interaction: discord.Interaction):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  if stop_script(REALTIME_SCRIPT):
    await interaction.response.send_message("Real-time calculations stopped.")
  else:
    await interaction.response.send_message(
        "Real-time script was not running.", ephemeral=True)



@bot.tree.command(name="scrims_calc_past",
                  description="Calculate past X custom games")
@app_commands.describe(number="Number of past scrims to calculate")
async def scrims_calc_past(interaction: discord.Interaction, number: int):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  await interaction.response.send_message(
      f"Calculating past {number} custom games...")


  process = await asyncio.create_subprocess_exec(
      "python",
      BATCH_SCRIPT,
      str(number),
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE)


  while True:
    line = await process.stdout.readline()
    if not line:
      break  

    decoded_line = line.decode().strip()
    print(decoded_line) 

    if "Completed batch processing." in decoded_line:
      await interaction.followup.send(
          f"✅ Done calculating past {number} custom games.")
      return  

  await process.wait()  



@bot.tree.command(name="team_add", description="Adds a team")
@app_commands.describe(tag="Team tag",
                       captain="Captain name",
                       member1="Member 1",
                       member2="Member 2",
                       member3="Member 3",
                       captain_opgg="Captain's op.gg link")
async def team_add(interaction: discord.Interaction, tag: str, captain: str,
                   member1: str, member2: str, member3: str,
                   captain_opgg: str):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  try:
    with open(TEAMS_JSON, "r") as file:
      teams = json.load(file)
  except (FileNotFoundError, json.JSONDecodeError):
    teams = {}

  teams[tag] = {
      "enabled": True,
      "players": {
          captain: captain_opgg,
          member1: "",
          member2: "",
          member3: ""
      },
      "captain": captain
  }

  with open(TEAMS_JSON, "w") as file:
    json.dump(teams, file, indent=4)

  await interaction.response.send_message(
      f"Team {tag} added with members: {captain}, {member1}, {member2}, {member3}. Captain's op.gg: {captain_opgg}"
  )



@bot.tree.command(name="team_remove", description="Removes a team by tag")
@app_commands.describe(tag="Team tag to remove")
async def team_remove(interaction: discord.Interaction, tag: str):
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return

  try:
    with open(TEAMS_JSON, "r") as file:
      teams = json.load(file)
  except (FileNotFoundError, json.JSONDecodeError):
    await interaction.response.send_message("No teams found.", ephemeral=True)
    return

  if tag in teams:
    del teams[tag]
    with open(TEAMS_JSON, "w") as file:
      json.dump(teams, file, indent=4)
    await interaction.response.send_message(f"Team {tag} has been removed.")
  else:
    await interaction.response.send_message(f"Team {tag} not found.",
                                            ephemeral=True)


@bot.tree.command(name="results", description="Get the latest scrim results")
async def results(interaction: discord.Interaction):
  await interaction.response.defer(
  )  
  if not has_permission(interaction):
    await interaction.response.send_message(
        "You don't have the required permissions to use this command",
        ephemeral=True)
    return


  process = await asyncio.create_subprocess_exec("python",
                                                 "screenshot_script.py")
  await process.communicate()  


  if os.path.exists(IMAGE_PATH):
    file = discord.File(IMAGE_PATH)
    await interaction.followup.send("**Latest Scrims Data:**", file=file)
  else:
    await interaction.followup.send(
        "No scrim results found. Please try again later.")


@bot.event
async def on_ready():
  print(f'Logged in as {bot.user}')
  try:
    bot.tree.clear_commands(guild=None)
    time.sleep(2)
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands successfully!")
  except Exception as e:
    print(f"Failed to sync commands: {e}")


bot.run(TOKEN)