import logging
from enum import Enum
from functools import lru_cache

import numpy as np
from essentia.standard import (
    MonoLoader,
    TensorflowPredict2D,
    TensorflowPredictMusiCNN,
)
from pydantic import BaseModel

from soundcloud_tools.predict.base import Predictor


class Mood(BaseModel):
    tag: str
    description: str
    descriptors: list[str]
    color: str
    color_name: str
    weight: float = 1.0


class MoodType(Enum):
    ENERGETIC = Mood(
        tag="energetic",
        description="High energy, dynamic, enthusiastic, often associated with bold and assertive music styles.",
        descriptors=["Passionate", "Rousing", "Confident", "Boisterous", "Rowdy"],
        color="#FF4500",
        color_name="red",
    )
    JOYFUL = Mood(
        tag="joyful",
        description="Bright, positive, lighthearted, and playful, reflecting happiness and warmth.",
        descriptors=["Amiable/Good-natured", "Sweet", "Fun", "Rollicking", "Cheerful"],
        color="#FFD700",
        color_name="orange",
    )
    MELANCHOLIC = Mood(
        tag="melancholic",
        description="Introspective and emotional, often evoking themes of nostalgia, sadness, or thoughtfulness.",
        descriptors=["Literate", "Wistful", "Bittersweet", "Autumnal", "Brooding", "Poignant"],
        color="#4682B4",
        color_name="blue",
    )
    PLAYFUL = Mood(
        tag="playful",
        description="Creative, quirky, and often comedic or playful, bringing a sense of humor or irony to the music.",
        descriptors=["Witty", "Humorous", "Whimsical", "Wry", "Campy", "Quirky", "Silly"],
        color="#9370DB",
        color_name="violet",
    )
    INTENSE = Mood(
        tag="intense",
        description="Powerful and dramatic, capturing tension, aggression, or emotional extremes.",
        descriptors=["Volatile", "Fiery", "Visceral", "Aggressive", "Tense/Anxious", "Intense"],
        color="#ffffff",
        color_name="gray",
        weight=0.5,
    )

    @classmethod
    def weights(cls) -> list[float]:
        return [mood.value.weight for mood in cls]

    @classmethod
    def values(cls):
        return [v.value for v in cls]

    @classmethod
    def get_mood_from_index(cls, index: int):
        return cls.values()[index]


@lru_cache
def load_embedding_model():
    return TensorflowPredictMusiCNN(
        graphFilename="msd-musicnn-1.pb",
        output="model/dense/BiasAdd",
    )


@lru_cache
def load_model():
    return TensorflowPredict2D(
        graphFilename="moods_mirex-msd-musicnn-1.pb",
        input="serving_default_model_Placeholder",
        output="PartitionedCall",
    )


def framewise_softmax(predictions):
    e_x = np.exp(predictions - np.max(predictions, axis=1, keepdims=True))  # Subtract max for numerical stability
    return e_x / e_x.sum(axis=1, keepdims=True)


# Time axis based on audio length and number of frames
# time = np.linspace(0, len(audio) / 44100, normalized_predictions.shape[0])  # Assuming 44.1kHz sample rate


def reweigh_predictions(predictions):
    return predictions * MoodType.weights()


def get_moods(predictions, level_threshold: float = 0.5, avg_threshold: float = 0.1) -> list[tuple[Mood, float]]:
    # Mean predictions over time
    preds = np.sum(predictions >= level_threshold, axis=0) / predictions.shape[0]
    return [(MoodType.get_mood_from_index(i), score) for i, score in enumerate(preds) if score >= avg_threshold]


def convert_predictions_to_classes(predictions) -> list[tuple[Mood, float]]:
    # Mean predictions over time
    preds = np.mean(predictions, axis=0)
    return [(MoodType.get_mood_from_index(i), score) for i, score in enumerate(preds)]


def predict(filename: str, embedding_model: TensorflowPredictMusiCNN, model: TensorflowPredict2D) -> np.ndarray:
    audio = MonoLoader(filename=filename, sampleRate=16000, resampleQuality=4)()
    logging.info(f"Audio shape {audio.shape}")
    embeddings = embedding_model(audio)
    logging.info(f"Embeddings Shape {embeddings.shape}")
    predictions = model(embeddings)
    return predictions


class MoodPredictor(Predictor):
    title: str = "Mood"
    help: str = "Predict the mood of the loaded track."

    def __init__(self):
        self.embedding_model = load_embedding_model()
        self.model = load_model()

    def predict(self, filename: str) -> list[tuple[str, float]]:
        predictions = predict(filename, self.embedding_model, self.model)
        moods = convert_predictions_to_classes(predictions)
        return [(mood.tag, score) for mood, score in moods]
