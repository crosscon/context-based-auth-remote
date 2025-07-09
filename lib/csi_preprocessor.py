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


def lowpass_filter(data, cutoff=0.1, order=4):
    b, a = butter(order, cutoff, btype='low')
    return filtfilt(b, a, data)


def bytes_to_amplitude_phase(raw_csi_bytes: bytes) -> tuple[list[float], list[float]]:
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

    delta_ampl = np.max(amplitude) - np.min(amplitude)
    amplitude = (amplitude - np.min(amplitude)) / (delta_ampl if delta_ampl != 0 else 1)  # min-max

    phase = list(np.unwrap(phase))
    delta_phase = np.max(phase) - np.min(phase)
    phase = (phase - np.min(phase)) / (delta_phase if delta_phase != 0 else 1)

    return amplitude, phase

    #csi_fingerprint = [amplitude, phase]

    #csi_fingerprint = torch.tensor(csi_fingerprint, dtype=torch.float64)  # [time, 2, subcarrier_idx]
    #print(csi_fingerprint.shape)
    #csi_fingerprint = csi_fingerprint.transpose(0, 1)  # [2, time, subcarrier_idx]
    #print(csi_fingerprint.shape)

    #return csi_fingerprint.tolist()


def records_to_tensor(csi_records: list[CSIRecord]) -> torch.tensor:
    amplitudes = []
    phases = []
    for record in csi_records:
        csi_bytes = record.get_csi_bytes()
        amplitude, phase = bytes_to_amplitude_phase(csi_bytes)
        amplitudes.append(amplitude)
        phases.append(phase)

    arr = np.array([[amplitudes, phases]])
    return torch.tensor(arr, dtype=torch.float)
