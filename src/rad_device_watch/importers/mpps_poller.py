from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from rad_device_watch.models import UsageRecord

logger = logging.getLogger(__name__)


class MppsPoller:
    def __init__(
        self,
        ae_title: str = "RAD_DEVICE_WATCH",
        pacs_host: str = "localhost",
        pacs_port: int = 11112,
        pacs_ae_title: str = "PACS",
        device_resolver: Callable[[str], int | None] | None = None,
    ):
        self.ae_title = ae_title
        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.pacs_ae_title = pacs_ae_title
        self.device_resolver = device_resolver

    def poll(self) -> list[UsageRecord]:
        try:
            from pydicom.dataset import Dataset
            from pynetdicom import AE
            from pynetdicom.sop_class import (
                ModalityPerformedProcedureStepRetrieve,
            )
        except ImportError:
            logger.error(
                "pynetdicom and pydicom are required for MPPS polling. "
                "Install with: pip install pynetdicom pydicom"
            )
            return []

        ae = AE(self.ae_title)
        ae.add_requested_context(ModalityPerformedProcedureStepRetrieve)

        records: list[UsageRecord] = []
        assoc = ae.associate(self.pacs_host, self.pacs_port, self.pacs_ae_title)

        if not assoc.is_established:
            logger.warning(
                "MPPS: Association not established with %s:%s",
                self.pacs_host,
                self.pacs_port,
            )
            return []

        try:
            identifier = Dataset()
            identifier.PerformedStationName = "*"

            status, results = assoc.send_n_get(
                identifier,
                ModalityPerformedProcedureStepRetrieve,
                "1.2.840.10008.3.1.2.3.4",
            )

            if status and results:
                for ds in results:
                    record = self._usage_record(ds)
                    if record is not None:
                        records.append(record)
            else:
                logger.info("MPPS N-GET returned no results or failed")
        except Exception as exc:
            logger.error("MPPS polling error: %s", exc)
        finally:
            assoc.release()

        logger.info("MPPS poll: retrieved %d usage records", len(records))
        return records

    def _usage_record(self, ds: object) -> UsageRecord | None:
        station = self._get_attr(ds, "PerformedStationName")
        status = self._get_attr(ds, "PerformedProcedureStepStatus")
        if not station or status != "COMPLETED":
            return None
        if self.device_resolver is None:
            logger.warning(
                "MPPS usage skipped for station '%s': no device resolver configured",
                station,
            )
            return None
        try:
            device_id = self.device_resolver(station)
        except Exception as exc:
            logger.warning("MPPS device resolution failed for station '%s': %s", station, exc)
            return None
        if device_id is None or device_id <= 0:
            logger.warning("MPPS usage skipped for unresolved station '%s'", station)
            return None

        start_date = self._get_attr(ds, "PerformedProcedureStepStartDate")
        date_str = (
            f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            if start_date and len(start_date) >= 8
            else datetime.now().strftime("%Y-%m-%d")
        )
        return UsageRecord(
            device_id=device_id,
            procedure_date=date_str,
            procedure_count=1,
            modality=self._get_attr(ds, "Modality"),
            source="mpps",
        )

    @staticmethod
    def _get_attr(ds, name: str) -> str | None:
        try:
            val = getattr(ds, name, None)
            if val is not None:
                return str(val).strip()
        except Exception:
            pass
        return None
