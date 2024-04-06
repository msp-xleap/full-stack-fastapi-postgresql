import random


class TextTypeSwapper:
    """
    A class to introduce typos and swap letters in a given text message.

    Attributes:
        _message (list): The message as a list of characters.
        _typo_prob (float): The probability of a character becoming a typo
            (between 0 and 1).
        _capitalization (list): A list of boolean values indicating the
            capitalization of each character in the message.
        _nearbykeys (dict): A dictionary mapping each letter to a list of
            nearby letters on the keyboard.
    """

    def __init__(self, text, typo_prob=0.025):
        """
        Initialize the TextTypeSwapper object.

        Args:
            text (str): The input message.
            typo_prob (float, optional): The probability of a character
                becoming a typo (between 0 and 1). Defaults to 0.025.
                15mistakes / 100 words = 15 mistakes / 600 characters = 0.025
                see https://www.grammarly.com/blog/analysis-shows-we-write-better-day/
                and https://contenthub-static.grammarly.com/blog/wp-content/
                uploads/2016/09/EarlyBird_NightOwl-Infographic-1.jpg
        """
        self._message = list(text)
        self._typo_prob = typo_prob
        self._capitalization = [False] * len(self._message)
        # Define nearby keys on the keyboard that can be swapped.
        # "": represents forgetting to type a character.
        self._nearbykeys = {
            "a": ["q", "w", "s", "x", "z", ""],
            "b": ["v", "g", "h", "n", ""],
            "c": ["x", "d", "f", "v", ""],
            "d": ["s", "e", "r", "f", "c", "x", ""],
            "e": ["w", "s", "d", "r", ""],
            "f": ["d", "r", "t", "g", "v", "c", ""],
            "g": ["f", "t", "y", "h", "b", "v", ""],
            "h": ["g", "y", "u", "j", "n", "b", ""],
            "i": ["u", "j", "k", "o", ""],
            "j": ["h", "u", "i", "k", "n", "m", ""],
            "k": ["j", "i", "o", "l", "m", ""],
            "l": ["k", "o", "p", ""],
            "m": ["n", "j", "k", "l", ""],
            "n": ["b", "h", "j", "m", ""],
            "o": ["i", "k", "l", "p", ""],
            "p": ["o", "l", ""],
            "q": ["w", "a", "s", ""],
            "r": ["e", "d", "f", "t", ""],
            "s": ["w", "e", "d", "x", "z", "a", ""],
            "t": ["r", "f", "g", "y", ""],
            "u": ["y", "h", "j", "i", ""],
            "v": ["c", "f", "g", "v", "b", ""],
            "w": ["q", "a", "s", "e", ""],
            "x": ["z", "s", "d", "c", ""],
            # Account for English and German keyboard layouts
            "y": ["t", "g", "h", "u", "a", "s", "x", "y", ""],
            "z": ["a", "s", "x", "y", "t", "g", "h", "u", ""],
            # Special characters
            " ": ["c", "v", "b", "n", "m"],
            ".": [",", "/", "-", " "],
            ",": ["m", ".", "/", " "],
            ":": [";", ".", " "],
            "'": ["", " "],
        }

    def add_typos(self):
        """
        Add typos to the message by replacing characters with nearby keyboard
        letters.
        """
        # Record capitalization
        for i in range(len(self._message)):
            self._capitalization[i] = self._message[i].isupper()
            self._message[i] = self._message[i].lower()

        # Add typos
        n_chars_to_flip = round(len(self._message) * self._typo_prob)
        pos_to_flip = random.sample(range(len(self._message)), n_chars_to_flip)

        for pos in pos_to_flip:
            try:
                typo_arrays = self._nearbykeys[self._message[pos]]
                new_char = random.choice(typo_arrays)
                self._message[pos] = new_char
            except Exception as e:
                print(e)
                continue

        # Restore capitalization
        for i in range(len(self._message)):
            if self._capitalization[i]:
                self._message[i] = self._message[i].upper()

        return self

    def get_text(self):
        """
        Get the modified message.

        Returns:
            str: The modified message.
        """
        return "".join(self._message)
