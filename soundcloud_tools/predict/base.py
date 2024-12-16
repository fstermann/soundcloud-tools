from abc import ABC, abstractmethod


class Predictor(ABC):
    title: str
    help: str

    @abstractmethod
    def predict(self, filename: str): ...
