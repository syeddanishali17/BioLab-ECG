"""Plain-language tooltips, used as `help=` on widgets and metrics."""

SNR = ("Signal-to-noise ratio in decibels. How strong the heartbeat is compared with the noise. "
       "24 dB: noise barely visible. 0 dB: noise as strong as the heartbeat. "
       "-6 dB: noise twice as strong.")
SE = ("Sensitivity (Se): of all true heartbeats, the share the detector found. "
      "Se = TP / (TP + FN). Low Se means missed beats.")
PPV = ("Positive predictivity (+P): of everything the detector called a beat, the share that "
       "really was one. +P = TP / (TP + FP). Low +P means false alarms.")
F1 = "F1: one number combining Se and +P (their harmonic mean)."
QRS = ("QRS complex: the sharp spike in the ECG produced by each heartbeat. "
       "QRS detectors look for it to locate beats.")
HR5 = ("Share of 10-second windows where the heart rate from the detector is within "
       "5 beats per minute of the heart rate from the reference annotations.")
CI = ("95% confidence interval from a block bootstrap: whole 10-second windows are resampled, "
      "because neighbouring beats share the same noise.")
NOISY_ONLY = ("Metrics are computed on the noisy segments only. Including the clean minutes "
              "would make every detector look better than it is.")
GAIN = "Noise gain a: the factor the noise recording is multiplied by to reach the target SNR."
PREFILTER = ("Optional extra filtering before the detector: 0.5 Hz high-pass (removes baseline "
             "wander) plus a 60 Hz notch (US mains). Applied forward-backward, so no time shift.")
TOLERANCE = ("A detection counts as correct if it lies within 150 ms of a reference beat, "
             "one-to-one. This follows the tolerance used in EC57-style evaluation.")
