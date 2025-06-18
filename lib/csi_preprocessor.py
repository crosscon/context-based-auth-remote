import math

import torch
import numpy as np
from scipy.signal import butter, filtfilt

import os
import dotenv

dotenv.load_dotenv()

ML_MODEL_SAMPLES_PER_RECORDING = int(os.environ.get("ML_MODEL_SAMPLES_PER_RECORDING"))



def csi_int16_from_bytes(b: bytes) -> list[int]:
    return [
        int.from_bytes(b[2*i:2*i+2], byteorder='little', signed=True)
        for i in range(len(b) // 2)
    ]


def lowpass_filter(data, cutoff=0.1, order=4):
    b, a = butter(order, cutoff, btype='low')
    return filtfilt(b, a, data)


def bytes_to_tensor(raw_csi_bytes: bytes) -> torch.tensor:
    csi_fingerprint = csi_int16_from_bytes(raw_csi_bytes)
    amplitude = []
    phase = []
    for j in range(0, 128, 2):
        real = csi_fingerprint[j]
        imag = csi_fingerprint[j + 1]
        amp = math.sqrt(real ** 2 + imag ** 2)
        phs = math.atan2(imag, real)
        amplitude.append(amp)  # [64]
        phase.append(phs)  # [64]

    amplitude = lowpass_filter(amplitude)
    amplitude = (amplitude - np.min(amplitude)) / (np.max(amplitude) - np.min(amplitude))  # min-max
    phase = list(np.unwrap(phase))
    phase = (phase - np.min(phase)) / (np.max(phase) - np.min(phase))

    csi_fingerprint = [amplitude, phase]

    csi_fingerprint = torch.tensor(csi_fingerprint, dtype=torch.float64)  # [time, 2, subcarrier_idx]
    csi_fingerprint = csi_fingerprint.transpose(0, 1)  # [2, time, subcarrier_idx]

    return csi_fingerprint.tolist()

