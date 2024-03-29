import logging
import re

from django.conf import settings


logger = logging.getLogger("calls")


def max_length_for_choices(choices):
    return max(len(v) for v in choices.values)


def is_subsequence(x, y):
    y_iter = iter(y)
    return all(any(x_item == y_item for y_item in y_iter) for x_item in x)


class __match_pronouncer_from_audio_file:
    def __init__(self):
        self.model = None

    def __call__(self, path, pronouncer) -> tuple[bool, list[str]]:
        if self.model is None:  # Saves memory on load
            from faster_whisper import WhisperModel

            self.model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")

        segments, _ = self.model.transcribe(path)
        heard_words = []
        for segment in segments:
            heard_words.extend(re.sub(r"[^a-z\s]", " ", segment.text.strip().lower()).strip().split())

        match = is_subsequence(pronouncer, heard_words)
        if not match:
            logger.warning(f"Couldn't match using Whisper: \"{' '.join(heard_words)}\" != \"{' '.join(pronouncer)}\"")

        return match, heard_words


match_pronouncer_from_audio_file = __match_pronouncer_from_audio_file()
