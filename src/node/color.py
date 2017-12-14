import colorama
from colorama import Fore, Back, Style


class Color:
    def __init__(self):
        colorama.init(autoreset=True)

    def I(self, text="INFO"):
        text = Fore.GREEN + text + Style.RESET_ALL
        return text

    def E(self, text="ERROR"):
        text = Fore.RED + text + Style.RESET_ALL
        return text

    def W(self, text="WARNING"):
        text = Fore.YELLOW + text + Style.RESET_ALL
        return text

    def C(self, text="TITLE"):
        text = Fore.CYAN + text + Style.RESET_ALL
        return text

    def M(self, text="TITLE"):
        text = Fore.MAGENTA + text + Style.RESET_ALL
        return text
