from torch import tensor

from .csi_preprocessor import records_to_tensor
from .ml_model import authenticate
from .csi_database import CSIDatabase, CSIRecord, csi_record_from_base64

import base64
import os


CSI_DATABASE_PATH = os.environ.get("CSI_DATABASE_PATH")
ML_MODEL_SAMPLES_PER_RECORDING = int(os.environ.get("ML_MODEL_SAMPLES_PER_RECORDING"))
ACCEPTANCE_THRESHOLD = float(os.environ.get("ACCEPTANCE_THRESHOLD"))

if None in [CSI_DATABASE_PATH, ML_MODEL_SAMPLES_PER_RECORDING]:
    raise Exception("Error: Missing Environment variable!")

DATABASE = CSIDatabase(CSI_DATABASE_PATH)



def decide(num_enrolled: int, num_stil_here: int, num_matches: int) -> bool:
    if num_enrolled == 0:
        return False

    return num_matches / num_enrolled >= ACCEPTANCE_THRESHOLD


def ml_compare(device_a: list[CSIRecord], device_b: list[CSIRecord]) -> bool | None:
    t1 = records_to_tensor(device_a)
    t2 = records_to_tensor(device_b)

    return authenticate(t1, t2)


def parse_order_records(collected_records: list[bytes]) -> dict[bytes, list[CSIRecord]]:
    parsed_records = [csi_record_from_base64(rec) for rec in collected_records]

    all_macs = { rec.get_mac_address_bytes() for rec in parsed_records }

    return {
        mac: [rec for rec in parsed_records if rec.get_mac_address_bytes() == mac]
        for mac in all_macs
    }


def get_filtered_records(parsed_ordered_records: dict[bytes, list[CSIRecord]]) -> dict[bytes, CSIRecord]:
    return {
        k: v
        for k, v in parsed_ordered_records.items()
        if len(v) >= ML_MODEL_SAMPLES_PER_RECORDING
    }


""" IMPORTANT: collected_records must be a list of BASE64-ENCODED records! """
def authenticate_device(device_id: str, collected_records: list[bytes]) -> bool:
    parsed_ordered_records = parse_order_records(collected_records)
    records = get_filtered_records(
        parsed_ordered_records
    )

    enrolled = DATABASE.get_enrolled_records(device_id)
    if enrolled == None:
        return False

    macs_enrolled = list(enrolled.keys())
    macs_still_here = [k for k in records.keys() if k in macs_enrolled]

    do_match = {
        mac: ml_compare(enrolled[mac], records[mac])
        for mac in macs_still_here
    }

    num_enrolled = len(macs_enrolled)
    num_still_here = len(macs_still_here)
    num_matches = sum(do_match.values())

    return decide(num_enrolled, num_still_here, num_matches)



""" IMPORTANT: collected_records must be a list of BASE64-ENCODED records! """
def enroll_device(device_id: str, collected_records: list[bytes]) -> bytes | None:
    parsed_ordered_records = parse_order_records(collected_records)
    records = get_filtered_records(
        parsed_ordered_records
    )

    filtered_records = [rec for l in records.values() for rec in l]
    filtered_macs = list(records.keys())

    if len(filtered_records) < 1:
        return None

    if DATABASE.enroll_csi_records(device_id, filtered_records):
        total_mac_bytes = bytes()
        for mac in filtered_macs:
            total_mac_bytes += mac
        return base64.b64encode(total_mac_bytes)

