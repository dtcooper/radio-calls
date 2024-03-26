from django.templatetags.static import static
import random
import string


from .constants import PIN_AUDIO_SPRITE_OFFSETS, WORDS_TO_PRONOUNCE, NUM_WORDS_FOR_PROUNCER


def max_length_for_choices(choices):
    return max(len(v) for v in choices.values)


def get_random_pronouncer_words():
    return random.sample(WORDS_TO_PRONOUNCE, NUM_WORDS_FOR_PROUNCER)


def generate_encoded_pin(pin):
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


class __decode_speech_file:
    WHISPER_MODEL = "tiny.en"

    def __init__(self):
        self.model = None

    def __call__(self, path):
        if self.model is None:
            import whisper  # Expensive import. Only use it on demand.

            self.model = whisper.load_model(self.WHISPER_MODEL)
        result = self.model.transcribe(path)
        return result["text"]


decode_speech_file = __decode_speech_file()
