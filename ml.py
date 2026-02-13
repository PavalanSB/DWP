"""
Machine learning module for digital wellness classification.

Uses a Decision Tree trained on:
  social_time, learning_time, entertainment_time, productivity_time, gaming_time,
  sleep_hours, stress_level, energy_level.

Outputs: Healthy, Moderate, Unhealthy, Burnout Risk.
Retrained on application startup with synthetic data.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sklearn.tree import DecisionTreeClassifier


@dataclass
class WellnessPrediction:
    label: str
    recommendation: str


def _recommendation_for_label(label: str) -> str:
    if label == "Healthy":
        return (
            "Your current digital balance looks healthy. "
            "Maintain consistent sleep (7–9 hours) and keep screen time in check. "
            "Consider short digital breaks every hour."
        )
    if label == "Moderate":
        return (
            "You are in a moderate wellness range. Try to reduce non-essential "
            "screen time by 30–60 minutes per day, and aim for at least 7 hours of sleep. "
            "Use focus modes during work or study periods."
        )
    if label == "Burnout Risk":
        return (
            "Your patterns suggest a higher risk of digital burnout. "
            "Prioritize reducing screen time, especially before sleep, aim for 7+ hours of rest, "
            "and consider daily offline windows. Take short breaks and monitor stress."
        )
    # Unhealthy
    return (
        "Your current pattern indicates a high-risk digital lifestyle. "
        "Prioritize reducing screen time, especially before sleep, and "
        "target at least 7 hours of quality sleep. Consider scheduling a "
        "daily digital detox window and using app limits."
    )


class WellnessModel:
    """
    Decision Tree classifier for digital wellness.

    Features (8): social_time, learning_time, entertainment_time, productivity_time,
                  gaming_time, sleep_hours, stress_level, energy_level.
    """

    def __init__(self) -> None:
        self.model = DecisionTreeClassifier(max_depth=5, random_state=42)
        self._is_trained = False
        self._train_on_synthetic_data()

    def _train_on_synthetic_data(self) -> None:
        """Train on synthetic patterns. Safe defaults for missing mood/stress/energy."""
        # [social, learning, entertainment, productivity, gaming, sleep, stress, energy]
        X = np.array([
            [60, 90, 45, 120, 30, 8, 2, 4],   # Healthy
            [90, 60, 60, 90, 20, 7.5, 2, 4],
            [120, 45, 90, 60, 45, 7, 3, 3],    # Moderate
            [150, 30, 120, 45, 60, 6.5, 3, 3],
            [180, 20, 150, 30, 90, 6, 4, 2],   # Unhealthy
            [200, 15, 180, 20, 120, 5.5, 4, 2],
            [240, 10, 200, 15, 150, 5, 5, 1],  # Burnout Risk
            [220, 20, 190, 25, 130, 5, 5, 2],
            [50, 120, 30, 150, 10, 8, 1, 5],   # Healthy
            [100, 80, 70, 80, 30, 7, 3, 3],   # Moderate
        ])
        y = np.array([
            "Healthy", "Healthy", "Moderate", "Moderate",
            "Unhealthy", "Unhealthy", "Burnout Risk", "Burnout Risk",
            "Healthy", "Moderate",
        ])
        self.model.fit(X, y)
        self._is_trained = True

    def predict(
        self,
        social_time: int,
        learning_time: int,
        entertainment_time: int,
        productivity_time: int,
        gaming_time: int,
        sleep_hours: float,
        stress_level: int,
        energy_level: int,
    ) -> WellnessPrediction:
        if not self._is_trained:
            self._train_on_synthetic_data()

        # Clamp stress/energy to 1-5 for model
        stress = max(1, min(5, stress_level or 3))
        energy = max(1, min(5, energy_level or 3))

        features = np.array([[
            social_time, learning_time, entertainment_time,
            productivity_time, gaming_time, sleep_hours, stress, energy
        ]])
        label = self.model.predict(features)[0]
        recommendation = _recommendation_for_label(label)
        return WellnessPrediction(label=label, recommendation=recommendation)


wellness_model = WellnessModel()
