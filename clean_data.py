import logging
import os
from typing import Optional
from urllib.parse import urlparse
import pandas as pd

# 1. ARCHITECTURAL LOGGING SYSTEM
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


class DataPreprocessingPipeline:
    """A production-grade pipeline to ingest, clean, normalize, and extract metrics

    from raw scraped web datasets for downstream AI/ML model consumption.
    """

    def __init__(self, input_filepath: str, output_filepath: str):
        self.input_path: str = input_filepath
        self.output_path: str = output_filepath
        self.df: Optional[pd.DataFrame] = None
        self.metrics: dict = {
            "initial_rows": 0,
            "final_rows": 0,
            "removed_duplicates": 0,
            "isolated_domains": 0,
        }

    def load_dataset(self) -> bool:
        """Safely ingests the Excel spreadsheet file into a Pandas memory frame."""
        if not os.path.exists(self.input_path):
            logging.error(
                f"Ingestion failed: Target source file '{self.input_path}' does"
                " not exist."
            )
            return False

        try:
            self.df = pd.read_excel(self.input_path)
            self.metrics["initial_rows"] = len(self.df)
            logging.info(
                f"Successfully ingested {self.metrics['initial_rows']} rows"
                f" from {self.input_path}"
            )
            return True
        except Exception as e:
            logging.critical(f"Fatal error reading storage layer: {e}")
            return False

    @staticmethod
    def extract_domain_host(url_string: str) -> str:
        """Structural string worker to safely isolate the root hostname from a URL."""
        try:
            if pd.isna(url_string) or not str(url_string).strip().startswith(
                "http"
            ):
                return ""
            parsed = urlparse(str(url_string).strip())
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""

    def process_pipeline(self) -> bool:
        """Executes defensive data cleaning transformations, column feature engineering,

        and data deduplication constraints.
        """
        if self.df is None or self.df.empty:
            logging.error("Pipeline Execution Halted: No active dataframe loaded.")
            return False

        try:
            # Step 1: Normalize structural column key spaces to prevent lookup crashes
            self.df.columns = self.df.columns.str.strip()

            # Target Column Variables
            headings_col = "Target Page Titles & Headings"
            links_col = "Extracted Resource Links"

            # Validate structural presence of target variables
            if headings_col not in self.df.columns or links_col not in self.df.columns:
                logging.error(
                    "Pipeline schema structural validation failed. Missing core"
                    " data columns."
                )
                return False

            # Step 2: Handle Missing Data (Imputation / Removal)
            # Replace NaN/Null structures in text columns safely with blank padding strings
            self.df[headings_col] = self.df[headings_col].fillna("").astype(str)
            self.df[links_col] = self.df[links_col].fillna("").astype(str)

            # Step 3: Text Normalization (Standardize casing for NLP tokenization)
            self.df[headings_col] = self.df[headings_col].str.upper().str.strip()

            # Step 4: Strict Row Filtering (Remove structural spacer padding rows)
            # Keep rows only where actual valid network tracking links exist
            self.df = self.df[self.df[links_col].str.startswith("http")]

            # Step 5: High-Performance Feature Engineering
            # Create a brand-new analytical column tracking the isolated domain network hosts
            logging.info("Executing analytical feature engineering transformations...")
            self.df["Extracted Network Host"] = self.df[links_col].apply(
                self.extract_domain_host
            )
            self.metrics["isolated_domains"] = self.df[
                "Extracted Network Host"
            ].nunique()

            # Step 6: Deduplication Optimization
            # Delete repetitive link records keeping only the first historical entry instance
            rows_before_dedup = len(self.df)
            self.df = self.df.drop_duplicates(subset=[links_col], keep="first")
            self.metrics["removed_duplicates"] = rows_before_dedup - len(
                self.df
            )

            self.metrics["final_rows"] = len(self.df)
            return True

        except Exception as e:
            logging.error(f"Execution Error inside core pipeline loop: {e}")
            return False

    def export_and_report(self):
        """Exports the clean matrix file down to disk storage and prints professional production metrics."""
        if self.df is None:
            return

        try:
            # Stream matrix cleanly out to Excel without exporting index row metrics
            self.df.to_excel(self.output_path, index=False)
            logging.info(
                f"CLEAN MATRIX SUCCESSFULLY STREAMED TO DISK: {self.output_path}"
            )

            # PRINT PRODUCTION PERFORMANCE REPORT METRICS
            print("\n" + "=" * 55)
            print("        PIPELINE RUN DATA PROCESSING METRICS REPORT       ")
            print("=" * 55)
            print(
                f"[+] Initial Database Entries Loaded : {self.metrics['initial_rows']} rows"
            )
            print(
                f"[+] Corrupted/Duplicate Rows Purged : {self.metrics['removed_duplicates']} rows"
            )
            print(
                f"[+] Unique Domain Targets Isolated  : {self.metrics['isolated_domains']} hosts"
            )
            print(
                f"[+] Final Cleaned Matrix Output Size: {self.metrics['final_rows']} rows"
            )
            print(
                f"[+] Efficiency Compression Ratio     : {((self.metrics['initial_rows'] - self.metrics['final_rows']) / self.metrics['initial_rows'] * 100):.2f}%"
            )
            print("=" * 55 + "\n")

        except Exception as e:
            logging.critical(f"Failed to compile storage layer export dump: {e}")


if __name__ == "__main__":
    # Define production configuration variables
    INPUT_DATA = "scraped_wikipedia.org.xlsx"
    CLEANED_OUTPUT = "cleaned_wikipedia_data.xlsx"

    # Instantiate and spin up the modular preprocessing machine pipeline pipeline
    pipeline = DataPreprocessingPipeline(
        input_filepath=INPUT_DATA, output_filepath=CLEANED_OUTPUT
    )

    if pipeline.load_dataset():
        if pipeline.process_pipeline():
            pipeline.export_and_report()
