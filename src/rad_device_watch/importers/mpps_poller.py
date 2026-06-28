from __future__ import annotations

import logging
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
    ):
        self.ae_title = ae_title
        self.pacs_host = pacs_host
        self.pacs_port = pacs_port
        self.pacs_ae_title = pacs_ae_title

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
                    station = self._get_attr(ds, "PerformedStationName")
                    modality = self._get_attr(ds, "Modality")
                    status_val = self._get_attr(
                        ds, "PerformedProcedureStepStatus"
                    )
                    start_date = self._get_attr(
                        ds, "PerformedProcedureStepStartDate"
                    )

                    if station and status_val == "COMPLETED":
                        date_str = (
                            f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
                            if start_date and len(start_date) >= 8
                            else datetime.now().strftime("%Y-%m-%d")
                        )
                        records.append(
                            UsageRecord(
                                device_id=0,
                                procedure_date=date_str,
                                procedure_count=1,
                                modality=modality,
                                source="mpps",
                            )
                        )
            else:
                logger.info("MPPS N-GET returned no results or failed")
        except Exception as exc:
            logger.error("MPPS polling error: %s", exc)
        finally:
            assoc.release()

        logger.info("MPPS poll: retrieved %d usage records", len(records))
        return records

    @staticmethod
    def _get_attr(ds, name: str) -> str | None:
        try:
            val = getattr(ds, name, None)
            if val is not None:
                return str(val).strip()
        except Exception:
            pass
        return None
