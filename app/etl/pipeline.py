import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.etl.categorization import CategorizationService
from app.etl.dedupe import compute_fingerprint
from app.etl.normalization import normalize_rappicard_transaction, normalize_transaction
from app.etl.parsers.bancolombia_xlsx_pesos import parse_bancolombia_xlsx_pesos
from app.etl.parsers.rappicard_davivienda_pdf import parse_rappicard_davivienda_pdf
from app.models import CategoryExample, RawRow, SourceFile, Transaction
from app.models.enums import BankEnum
from app.services.llm_client import OpenRouterClient

logger = logging.getLogger(__name__)


class ETLPipeline:
    def __init__(self, db: Session):
        self.db = db

    def process_file(self, file_id: UUID) -> dict:
        """
        Process a source file through the ETL pipeline.

        Returns:
            dict: {
                "parsed_rows": int,
                "inserted_transactions": int,
                "duplicates_skipped": int,
                "status": str
            }
        """
        # Get source file (account is eager-loaded via joined relationship)
        source_file = self.db.query(SourceFile).filter(SourceFile.id == file_id).first()
        if not source_file:
            raise ValueError(f"Source file {file_id} not found")

        if source_file.parse_status == "PROCESSED":
            logger.warning(f"File {file_id} already processed")
            return {
                "parsed_rows": 0,
                "inserted_transactions": 0,
                "duplicates_skipped": 0,
                "status": "ALREADY_PROCESSED",
            }

        try:
            # Stage 1: Parse
            file_path = Path(source_file.storage_uri)
            parsed_rows, normalizer = self._parse_file(source_file, file_path)

            # Stage 2: Normalize and persist
            result = self._normalize_and_persist(source_file, parsed_rows, normalizer)

            # Update status
            source_file.parse_status = "PROCESSED"
            self.db.commit()

            return {
                "parsed_rows": len(parsed_rows),
                "inserted_transactions": result["inserted"],
                "duplicates_skipped": result["duplicates"],
                "status": "PROCESSED",
            }

        except Exception as e:
            logger.error(f"ETL failed for file {file_id}: {e}")
            source_file.parse_status = "FAILED"
            self.db.commit()
            raise

    def _to_jsonable(self, obj):
        """Recursively convert date/Decimal to JSON-serializable types."""
        if isinstance(obj, dict):
            return {k: self._to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._to_jsonable(v) for v in obj]
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        return obj

    def _parse_file(self, source_file: SourceFile, file_path: Path) -> tuple[list[dict], callable]:
        """Parse file based on bank and file type. Returns (rows, normalizer)."""
        bank = source_file.account.bank_name
        file_type = source_file.file_type

        if bank == BankEnum.BANCOLOMBIA and file_type == "xlsx":
            return parse_bancolombia_xlsx_pesos(file_path), normalize_transaction

        if bank == BankEnum.RAPPI and file_type == "pdf":
            return parse_rappicard_davivienda_pdf(file_path), normalize_rappicard_transaction

        raise ValueError(
            f"Unsupported bank/file_type: {bank}/{file_type}"
        )

    def _build_categorization_service(self) -> CategorizationService:
        examples = self.db.query(CategoryExample).all()
        examples_dicts = [
            {"description_clean": e.description_clean, "category": e.category.value, "merchant": e.merchant}
            for e in examples
        ]
        llm_client = OpenRouterClient()
        return CategorizationService(examples=examples_dicts, llm_client=llm_client)

    def _normalize_and_persist(
        self, source_file: SourceFile, parsed_rows: list[dict], normalizer
    ) -> dict:
        """Normalize, categorize, and persist transactions."""
        inserted = 0
        duplicates = 0

        categorizer = self._build_categorization_service()

        for idx, raw_tx in enumerate(parsed_rows):
            # Normalize
            normalized = normalizer(raw_tx)

            # Categorize
            cat = categorizer.categorize({**normalized, "details_json": normalized["details_json"]})

            # Compute fingerprint
            fingerprint = compute_fingerprint(source_file_id=source_file.id, row_index=idx)

            # Create transaction
            transaction = Transaction(
                source_file_id=source_file.id,
                posted_at=normalized["posted_at"],
                description_raw=normalized["description_raw"],
                description_clean=normalized["description_clean"],
                amount=normalized["amount"],
                currency=raw_tx.get("currency", "COP"),
                fingerprint=fingerprint,
                details_json=normalized["details_json"],
                category=cat.category,
                category_confidence=cat.category_confidence,
                category_method=cat.category_method,
                merchant_guess=cat.merchant_guess,
            )

            try:
                with self.db.begin_nested():
                    self.db.add(RawRow(
                        source_file_id=source_file.id,
                        row_index=idx,
                        raw_data_json=self._to_jsonable(raw_tx),
                    ))
                    self.db.add(transaction)
                inserted += 1
            except IntegrityError:
                # Duplicate fingerprint — savepoint rolled back, outer tx intact
                duplicates += 1
                logger.warning(
                    "Duplicate fingerprint skipped — row_index=%d date=%s amount=%s desc=%s fingerprint=%s",
                    idx,
                    normalized["posted_at"],
                    normalized["amount"],
                    normalized["description_clean"],
                    fingerprint,
                )

        self.db.commit()

        return {
            "inserted": inserted,
            "duplicates": duplicates,
        }
