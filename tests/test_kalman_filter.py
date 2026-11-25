import pytest
from src.core.kalman_filter import KalmanDurationEstimator

def test_initial_measurement():
    estimator = KalmanDurationEstimator()

    result = estimator.update(2.5)

    assert result == 2.5


def test_estimate_updates_with_new_measurements():
    estimator = KalmanDurationEstimator()

    estimator.update(2.0)
    result = estimator.update(3.0)

    assert 2.0 < result < 3.0


def test_estimate_duration_with_multiple_measurements():
    estimator = KalmanDurationEstimator()

    result = estimator.estimate_duration([2.4, 2.1, 2.3])

    assert 2.1 < result < 2.4


def test_invalid_measurement():
    estimator = KalmanDurationEstimator()

    with pytest.raises(ValueError):
        estimator.update(-2)


def test_empty_measurements():
    estimator = KalmanDurationEstimator()

    with pytest.raises(ValueError):
        estimator.estimate_duration([])
