
class KalmanDurationEstimator:
    """
    Estimates test execution duration using a
    one-dimensional Kalman Filter.
    """

    def __init__(
        self,
        process_variance=0.01,
        measurement_variance=0.1,
        initial_estimate=0.0
    ):
        if process_variance < 0:
            raise ValueError("Process variance cannot be negative.")

        if measurement_variance <= 0:
            raise ValueError("Measurement variance must be positive.")

        self.process_variance = process_variance
        self.measurement_variance = measurement_variance

        self.estimate = initial_estimate
        self.error_covariance = 1.0
        self.initialized = initial_estimate > 0

    def update(self, measurement):
        """Update the estimated duration using a new measurement."""

        if measurement <= 0:
            raise ValueError("Duration measurement must be positive.")

        if not self.initialized:
            self.estimate = measurement
            self.initialized = True
            return self.estimate

        # Prediction step
        self.error_covariance += self.process_variance

        # Kalman gain
        kalman_gain = (
            self.error_covariance
            / (self.error_covariance + self.measurement_variance)
        )

        # Update estimate
        self.estimate += kalman_gain * (
            measurement - self.estimate
        )

        # Update uncertainty
        self.error_covariance *= (1 - kalman_gain)

        return self.estimate

    def estimate_duration(self, measurements):
        """Process multiple measurements and return the final estimate."""

        if not measurements:
            raise ValueError("At least one measurement is required.")

        for measurement in measurements:
            self.update(measurement)

        return self.estimate
