import math

import torch
import numpy as np
from scipy.signal import butter, filtfilt

import os
import dotenv

from .csi_database import CSIRecord

dotenv.load_dotenv()

ML_MODEL_SAMPLES_PER_RECORDING = int(os.environ.get("ML_MODEL_SAMPLES_PER_RECORDING"))



def csi_int16_from_bytes(b: bytes) -> list[int]:
    return [
        int.from_bytes(b[2*i:2*i+2], byteorder='little', signed=True)
        for i in range(len(b) // 2)
    ]


def bytes_to_amplitude_phase(raw_csi_bytes: bytes) -> list[float]:
    csi_fingerprint = csi_int16_from_bytes(raw_csi_bytes)
    amplitude = []
    for j in range(0, 128, 2):
        if j in [0, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74]:
            continue
        real = csi_fingerprint[j]
        imag = csi_fingerprint[j + 1]
        amplitude.append(math.sqrt(real ** 2 + imag ** 2))  # [52]


    delta_ampl = np.max(amplitude) - np.min(amplitude)
    amplitude = (amplitude - np.min(amplitude)) / (delta_ampl if delta_ampl != 0 else 1)  # min-max normalization

    return amplitude
    #csi_fingerprint = [amplitude, phase]

    #csi_fingerprint = torch.tensor(csi_fingerprint, dtype=torch.float64)  # [time, 2, subcarrier_idx]
    #print(csi_fingerprint.shape)
    #csi_fingerprint = csi_fingerprint.transpose(0, 1)  # [2, time, subcarrier_idx]
    #print(csi_fingerprint.shape)

    #return csi_fingerprint.tolist()


def records_to_tensor(csi_records: list[CSIRecord]) -> torch.tensor:
    amplitudes = []
    for record in csi_records:
        csi_bytes = record.get_csi_bytes()
        amplitude = bytes_to_amplitude_phase(csi_bytes)
        amplitudes.append(amplitude)

    arr = np.array([[amplitudes]])
    return torch.tensor(arr, dtype=torch.float)