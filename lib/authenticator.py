from .csi_preprocessor import bytes_to_tensor
from .ml_model import authenticate
from .csi_database import CSIDatabase, CSIRecord, csi_record_from_base64

import os


CSI_DATABASE_PATH = os.environ.get("CSI_DATABASE_PATH")
ML_MODEL_SAMPLES_PER_RECORDING = int(os.environ.get("ML_MODEL_SAMPLES_PER_RECORDING"))

if None in [CSI_DATABASE_PATH, ML_MODEL_SAMPLES_PER_RECORDING]:
    raise Exception("Error: Missing Environment variable!")

DATABASE = CSIDatabase(CSI_DATABASE_PATH)



def decide(num_enrolled: int, num_stil_here: int, num_matches: int) -> bool:
    return False


def ml_compare(device_a: list[CSIRecord], device_2: list[CSIRecord]) -> bool | None:
    pass


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
        for k, v in parse_order_records.items()
        if len(v) >= ML_MODEL_SAMPLES_PER_RECORDING
    }



def authenticate_device(device_id: str, collected_records: list[bytes]) -> bool:
    records = get_filtered_records(
        parsed_ordered_records(collected_records)
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



def enroll_device(device_id: str, collected_records: list[bytes]) -> bytes | None:
    records = get_filtered_records(
        parsed_ordered_records(collected_records)
    )

    filtered_records = [rec for l in records.items() for rec in l]
    filtered_macs = list(records.keys())

    if len(filtered_records) < 1:
        return None

    if DATABASE.enroll_csi_records(device_id, filtered_records):
        return filtered_macs

