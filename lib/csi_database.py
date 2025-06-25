from base64 import b64encode, b64decode
import os
import shutil


def stringify_mac(mac_address: bytes) -> str:
    return "-".join([hex(b)[2:] for b in mac_address])


class CSIRecord():

    def __init__(self, raw: bytes):
        self.__raw = raw


    def get_rssi(self) -> int:
        return int.from_bytes(self.__raw[0], signed=True)


    def get_mac_address_bytes(self) -> bytes:
        return self.__raw[1:7]


    def get_mac_address(self) -> str:
        return stringify_mac(
            self.get_mac_address_bytes()
        )


    def get_time_offset(self) -> int:
        return int.from_bytes(self.__raw[9:11], byteorder="little", signed=False)


    def get_csi_bytes(self) -> bytes:
        return self.__raw[11:]


    def get_as_raw_bytes(self) -> bytes:
        return self.__raw


def csi_record_from_base64(b64encoded: str) -> CSIRecord:
    return CSIRecord(
        b64decode(
            b64encoded
        )
    )


def csi_record_to_base64(record: CSIRecord) -> bytes:
    return b64encode(
        record.get_as_raw_bytes()
    ).decode()



class CSIDatabase():

    def __init__(self, path: str) -> None:
        self.__path = path


    def __device_path(self, device_id: str) -> str:
        return os.path.join(self.__path, device_id)


    def __dataset_path(self, device_id: str, mac_address: str) -> str:
        return os.path.join(
            self.__device_path(device_id),
            mac_address
        )


    def is_device_enrolled(self, device_id: str) -> bool:
        return os.path.exists(
            self.__device_path(device_id)
        )


    def enroll_csi_records(self, device_id: str, csi_records: list[CSIRecord]) -> bool:
        if self.is_device_enrolled(device_id):
            return False

        try:
            os.makedirs(self.__device_path(device_id), exist_ok=True)

            macs = { record.get_mac_address() for record in csi_records }

            for mac in macs:
                records = [s for s in csi_records if s.get_mac_address() == mac]
                records_enc = [csi_record_to_base64(r) for r in records]
                records_concat = "\n".join(records_enc)

                with open(self.__dataset_path(device_id, mac), "w") as f:
                    f.write(records_concat)

            return True
        except Exception as e:
            self.revoke_csi_records(device_id)


    def get_enrolled_records(self, device_id: str) -> dict[bytes, list[CSIRecord]] | None:
        if not self.is_device_enrolled(device_id):
            return None

        try:
            ret = dict()

            for file in os.listdir(self.__device_path(device_id)):
                if file.startswith("."):
                    continue

                with open(self.__dataset_path(device_id, file)) as f:
                    raw = f.read()

                indiv = [e for e in raw.split("\n") if len(e) > 0]
                records = [csi_record_from_base64(enc) for enc in indiv]

                ret[file] = records

            return ret
        except:
            return None


    def revoke_csi_records(self, device_id: str) -> bool:
        try:
            shutil.rmtree(self.__device_path(device_id), ignore_errors=True)
            return True
        except:
            return False
