import random
import re
import string

from django.conf import settings
from django.templatetags.static import static

from .constants import NUM_WORDS_FOR_PROUNCER, PIN_AUDIO_SPRITE_OFFSETS, PIN_LENGTH, WORDS_TO_PRONOUNCE


def max_length_for_choices(choices):
    return max(len(v) for v in choices.values)


def generate_pronouncer():
    return random.sample(WORDS_TO_PRONOUNCE, NUM_WORDS_FOR_PROUNCER)


def encode_pin(pin):
    encoded_digits = set()
    while len(encoded_digits) < 10:
        encoded_digits.add("".join(random.choice(string.ascii_letters) for _ in range(12)))

    encoded_digits = list(encoded_digits)
    random.shuffle(encoded_digits)

    encoded_pin = [encoded_digits[int(d)] for d in pin]
    offsets = list(zip(encoded_digits, PIN_AUDIO_SPRITE_OFFSETS))

    random.shuffle(offsets)
    return {
        "code": encoded_pin,
        "offsets": dict(offsets),
        "pin_audio_url": static("api/hit/numbers.mp3"),
    }


def generate_pin():
    return "".join(random.choice(string.digits) for _ in range(PIN_LENGTH))


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


class __match_pronouncer_from_audio_file:
    def __init__(self):
        self.model = None

    def __call__(self, path, pronouncer):
        if self.model is None:  # Saves memory on load
            from faster_whisper import WhisperModel

            self.model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")

        segments, _ = self.model.transcribe(path)
        heard_words = []
        for segment in segments:
            heard_words.extend(re.sub(r"[^a-z\s]", " ", segment.text.strip().lower()).strip().split())

        match = is_subsequence(pronouncer, heard_words)

        print(f"expected words: {pronouncer}")
        print(f"   heard words: {heard_words}")
        print(f"         match: {match}")
        return match


match_pronouncer_from_audio_file = __match_pronouncer_from_audio_file()
