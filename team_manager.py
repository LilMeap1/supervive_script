import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit,
    QLabel, QMenu, QListWidget, QListWidgetItem, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import Qt
import json
import re

# File paths
TEAM_FILE = "teams.json"
PLAYER_FILE = "players.json"

# Load data functions
def load_json(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

class TeamManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Team Manager")
        self.setGeometry(100, 100, 800, 500)  # Increased width for parallel layout

        # Load existing teams and players
        self.teams = load_json(TEAM_FILE)
        self.players = load_json(PLAYER_FILE)

        layout = QVBoxLayout()

        # Horizontal Layout for Parallel Lists
        list_layout = QHBoxLayout()

        # Team List
        self.team_list = QListWidget()
        self.team_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.team_list.customContextMenuRequested.connect(self.show_team_context_menu)
        list_layout.addWidget(self.team_list)

        # Unassigned Players List
        self.unassigned_list = QListWidget()
        list_layout.addWidget(self.unassigned_list)

        layout.addLayout(list_layout)

        self.update_team_list()
        self.update_unassigned_list()

        # Team Inputs
        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText("Enter team tag")
        layout.addWidget(QLabel("Team Name:"))
        layout.addWidget(self.team_name_input)

        self.player_inputs = []
        for i in range(4):
            player_input = QLineEdit()
            player_input.setPlaceholderText(f"Enter Player {i + 1} Name")
            self.player_inputs.append(player_input)
            layout.addWidget(QLabel(f"Player {i + 1}:"))
            layout.addWidget(player_input)

        # Add Team Button
        self.add_team_button = QPushButton("Add Team")
        self.add_team_button.clicked.connect(self.add_team)
        layout.addWidget(self.add_team_button)

        # Player Management Section
        self.player_name_input = QLineEdit()
        self.player_name_input.setPlaceholderText("Enter Player Name")
        layout.addWidget(QLabel("Add New Player:"))
        layout.addWidget(self.player_name_input)

        self.player_url_input = QLineEdit()
        self.player_url_input.setPlaceholderText("Enter Player op.gg URL")
        layout.addWidget(QLabel("Player op.gg Link:"))
        layout.addWidget(self.player_url_input)

        # Add Player Button
        self.add_player_button = QPushButton("Add Player to Database")
        self.add_player_button.clicked.connect(self.add_player)
        layout.addWidget(self.add_player_button)

        # Set Layout
        self.setLayout(layout)

    def update_team_list(self):
        self.team_list.clear()
        for team, team_data in self.teams.items():
            formatted_players = [self.players.get(p, p) for p in team_data["players"]]
            display_players = [self.extract_name(p) for p in formatted_players]
            item_text = f"{team}: {', '.join(display_players)}"
            item = QListWidgetItem(item_text)
            
            # Checkbox for enabling/disabling teams
            item.setCheckState(Qt.CheckState.Checked if team_data["enabled"] else Qt.CheckState.Unchecked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.ItemDataRole.UserRole, team)  # Store team name in item data
            self.team_list.addItem(item)

        self.team_list.itemChanged.connect(self.toggle_team_enabled)

    def update_unassigned_list(self):
        self.unassigned_list.clear()
        assigned_players = {player for team in self.teams.values() for player in team["players"]}
        unassigned_players = [name for name in self.players.keys() if name not in assigned_players]

        for player in unassigned_players:
            self.unassigned_list.addItem(player)

    def toggle_team_enabled(self, item):
        team_name = item.data(Qt.ItemDataRole.UserRole)  # Retrieve team name from item data
        self.teams[team_name]["enabled"] = item.checkState() == Qt.CheckState.Checked
        save_json(TEAM_FILE, self.teams)

    def add_team(self):
        team_name = self.team_name_input.text().strip()
        if not team_name:
            QMessageBox.warning(self, "Error", "Please enter a team name.")
            return

        player_names = [p.text().strip() for p in self.player_inputs if p.text().strip()]
        if len(player_names) != 4:
            QMessageBox.warning(self, "Error", "Each team must have exactly 4 players.")
            return
        
        # Validate player names exist in player list
        missing_players = [p for p in player_names if p not in self.players]
        if missing_players:
            QMessageBox.critical(self, "Error", f"Players not found: {', '.join(missing_players)}.\nPlease add them first.")
            return

        # Convert player names to URLs using players.json
        player_urls = [self.players.get(name, name) for name in player_names]  # Use name if URL not found
        self.teams[team_name] = {"players": player_urls, "enabled": True}
        save_json(TEAM_FILE, self.teams)
        self.update_team_list()
        self.update_unassigned_list()

        # Clear inputs
        self.team_name_input.clear()
        for p in self.player_inputs:
            p.clear()

    def add_player(self):
        player_name = self.player_name_input.text().strip()
        player_url = self.player_url_input.text().strip()

        if not player_name or not player_url:
            QMessageBox.warning(self, "Error", "Both fields are required.")
            return

        # Save to players.json
        self.players[player_name] = player_url
        save_json(PLAYER_FILE, self.players)

        QMessageBox.information(self, "Success", f"Added {player_name} to player database.")
        self.player_name_input.clear()
        self.player_url_input.clear()

        self.update_unassigned_list()

    def show_team_context_menu(self, position):
        item = self.team_list.itemAt(position)
        if item:
            menu = QMenu()
            edit_action = menu.addAction("Edit Team")
            delete_action = menu.addAction("Delete Team")

            action = menu.exec(self.team_list.mapToGlobal(position))
            if action == edit_action:
                self.edit_team(item.data(Qt.ItemDataRole.UserRole))
            elif action == delete_action:
                self.delete_team(item.data(Qt.ItemDataRole.UserRole))

    def edit_team(self, team_name):
        if team_name in self.teams:
            self.team_name_input.setText(team_name)
            player_urls = self.teams[team_name]["players"]
            for i, url in enumerate(player_urls):
                player_name = next((k for k, v in self.players.items() if v == url), url)
                self.player_inputs[i].setText(player_name)
            del self.teams[team_name]
            save_json(TEAM_FILE, self.teams)
            self.update_team_list()
            self.update_unassigned_list()

    def delete_team(self, team_name):
        if team_name in self.teams:
            del self.teams[team_name]
            save_json(TEAM_FILE, self.teams)
            self.update_team_list()
            self.update_unassigned_list()

    @staticmethod
    def extract_name(url):
        match = re.search(r"steam-(.*?)%", url)
        return match.group(1) if match else url

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TeamManager()
    window.show()
    sys.exit(app.exec())
