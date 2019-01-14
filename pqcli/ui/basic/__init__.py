import argparse
import enum
import logging
import signal
import sys
import time
import typing as T
from datetime import datetime, timedelta

from pqcli import lingo
from pqcli.config import CLASSES, PRIME_STATS, RACES
from pqcli.mechanic import Player, Simulation, StatsBuilder, create_player
from pqcli.roster import Roster
from pqcli.ui.base import BaseUserInterface

LOGO = """
 ____                                     ___                  _
|  _ \ _ __ ___   __ _ _ __ ___  ___ ___ / _ \ _   _  ___  ___| |_
| |_) | '__/ _ \ / _` | '__/ _ \/ __/ __| | | | | | |/ _ \/ __| __|
|  __/| | | (_) | (_| | | |  __/\__ \__ \ |_| | |_| |  __/\__ \ |_
|_|   |_|  \___/ \__, |_|  \___||___/___/\__\_\\\\__,_|\___||___/\__|
                 |___/
"""


class MainMenu(enum.IntEnum):
    create = 1
    play = 2
    info = 3
    delete = 4
    quit = 5


class BasicUserInterface(BaseUserInterface):
    def __init__(self, roster: Roster, args: argparse.Namespace) -> None:
        super().__init__(roster, args)

        def signal_handler(sig: T.Any, frame: T.Any) -> None:
            logging.info("Quitting")
            if self.args.use_saves:
                self.roster.save()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

    def run(self) -> None:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="[%(asctime)s] %(message)s",
        )

        self.logo()
        self.main_menu()

    def logo(self) -> None:
        print(LOGO)

    def main_menu(self) -> None:
        while True:
            choice = self.menu(
                [
                    (MainMenu.create, "Create a new character"),
                    (MainMenu.play, "Play as character"),
                    (MainMenu.info, "Query character info"),
                    (MainMenu.delete, "Delete a character"),
                    (MainMenu.quit, "Quit"),
                ]
            )

            if choice == MainMenu.create:
                player = self.create_player()

            elif choice == MainMenu.play:
                player = self.choose_player()
                if not player:
                    continue
                self.play(player)

            elif choice == MainMenu.info:
                player = self.choose_player()
                if not player:
                    continue
                self.print_player_info(player)

            elif choice == MainMenu.delete:
                player = self.choose_player()
                if not player:
                    continue
                self.delete_player(player)

            elif choice == MainMenu.quit:
                self.quit()
                break

    def create_player(self) -> T.Optional[Player]:
        name = input("Name your new character: ")
        if not name:
            print("Cancelled.")
            return None

        race = self.menu([(race, race.name) for race in RACES])
        class_ = self.menu([(class_, class_.name) for class_ in CLASSES])

        stats_builder = StatsBuilder()
        while True:
            stats = stats_builder.roll()
            for stat in PRIME_STATS:
                print(f"{stat.value}: {stats[stat]}")
            print(f"Total: {sum(stats[stat] for stat in PRIME_STATS)}")
            if self.confirm("Is this okay?"):
                break

        player = create_player(
            name=name, race=race, class_=class_, stats=stats
        )
        self.roster.players.append(player)
        if self.confirm("Do you want to play as your new character?"):
            self.play(player)
        return player

    def play(self, player: Player) -> None:
        print(f"Playing as {player.name}")
        simulation = Simulation(player)
        last_save = datetime.now()
        last_tick = datetime.now()
        last_level = 0
        while True:
            elapsed = datetime.now() - last_tick
            simulation.tick(elapsed.total_seconds() * 1000)
            last_tick = datetime.now()
            wait = (timedelta(milliseconds=100) - elapsed).total_seconds()
            wait = max(0, wait)
            time.sleep(wait)
            if player.level != last_level:
                last_level = player.level
                self.print_player_info(player)
            if self.args.use_saves:
                self.roster.save_periodically()

    def print_player_info(self, player: Player) -> None:
        print("--- Character Sheet ---")
        print(f"Name: {player.name}")
        print(f"Race: {player.race.name}")
        print(f"Class: {player.class_.name}")
        print(f"Level: {player.level}")
        print()
        for stat, value in player.stats:
            print(f"{stat.value}: {value}")
        print()
        print("--- Spell Book ---")
        if not player.spell_book:
            print("No spells memorized yet.")
        else:
            for spell in player.spell_book:
                print(f"{spell.name} {lingo.to_roman(spell.level)}")
        print()
        print("--- Equipment ---")
        for equipment_type, name in player.equipment:
            print(f"{equipment_type.value}: {name}")
        print()
        print("--- Inventory ---")
        print(f"Gold: {player.inventory.gold}")
        for item in player.inventory:
            print(f"{item.name}: {item.quantity}")
        print()
        print("--- Plot ---")
        print(f"Current act: {lingo.to_roman(player.quest_book.act)}")
        print(f"Current quest: {player.quest_book.current_quest or '?'}")
        print(
            f"Current task: {player.task.description if player.task else '?'}"
        )

    def delete_player(self, player: Player) -> None:
        if self.confirm(lingo.terminate_message(player.name)):
            del self.roster.players[self.roster.players.index(player)]

    def quit(self) -> None:
        if self.args.use_saves:
            self.roster.save()

    def choose_player(self) -> T.Optional[Player]:
        if not self.roster.players:
            print("No characters to choose from!")
            return None

        return self.menu(
            [(player, player.name) for player in self.roster.players],
            title="Choose your character",
        )

    def confirm(self, message: str) -> bool:
        while True:
            choice = input(f"{message} [y/n] ")
            if choice.lower() in {"y", "yes", "1"}:
                return True
            if choice.lower() in {"n", "no", "0"}:
                return False

    def menu(
        self,
        options: T.Sequence[T.Tuple[T.Any, str]],
        title: T.Optional[str] = None,
    ) -> T.Any:
        print()
        if title:
            print(f"{title}:")
        for i, item in enumerate(options, 1):
            _, description = item
            print(f"{i}) {description}")
        print()

        while True:
            try:
                num = int(input("Your choice: "))
            except ValueError:
                print("Not a number")
                continue
            if num not in range(1, len(options) + 1):
                print(f"Expected a number betwen 1..{len(options)}")
                continue
            return options[num - 1][0]
