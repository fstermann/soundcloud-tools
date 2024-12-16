from essentia.standard import MonoLoader, RhythmExtractor2013

from soundcloud_tools.predict.base import Predictor


class BPMPredictor(Predictor):
    title: str = "BPM"
    help: str = "Predict the BPM of the loaded track."

    def predict(self, filename: str) -> int:
        audio = MonoLoader(filename=filename)()
        rhythm_extractor = RhythmExtractor2013(method="multifeature")
        bpm, *_ = rhythm_extractor(audio)
        return round(bpm)
