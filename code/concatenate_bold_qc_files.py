"""Run this script in the root directory of a <study>_CPAC repo
to concatenate BOLD QC data for each *_bold.nii.gz file.

This script fixes some of the issues with the cpac qc tsvs,
namely that the acquisition isn't included in the quality.tsv file.

"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

NO_SES_STUDIES = {
    "CCNP": 1,
    "PNC": "PNC1",
}


def get_jenkinson_fd(qc_file):
    """Get the median jenkinson fd from a CPAC/AFNI 1D file.

    These are in a separate 1D file that contains whitespace
    separated floating point values.

    NOTE:
    -----

    We are intentionally removing the first FC value to be
    consistent with the fmriprep method of measuring FD. In
    fmriprep the first FD value is set to NAN.
    """
    qc_stem = qc_file.name.split("space-")[0]
    paired_jenkinson = list(
        qc_file.parent.glob(f"{qc_stem}*desc-FDJenkinson_motion.1D")
    )

    if len(paired_jenkinson) > 1:
        logging.warning(
            f"found too many ({len(paired_jenkinson)}) jenkinson fds for {qc_file}"
        )
        return np.inf
    if not paired_jenkinson:
        logging.warning(f"unable to find jenkinson fd for {qc_file}")
        return np.inf

    jenkinson_vals = np.loadtxt(paired_jenkinson[0])
    # Get the median from everything BUT the first value
    return np.median(jenkinson_vals[1:])


def concatenate_bold_qc(study_name, bold_dir):
    """Create a group qc tsv for cpac outputs.

    This loops over all the available xcp_quality.tsv files and
    concatenates them into a single tsv. Since the Jenkinson FD is
    not included in the CPAC xcp_quality.tsv files, another file
    is loaded (the corresponding FDJenkinson_motion.1D) and the
    median of all but the first FD values is calculated.

    If there is an error on this function it is most likely due to
    the data not being available in the local annex. Be sure to

    ```bash
    datalad get \
        cpac_RBCv0/sub-*/ses-*/func/*reg-36Parameter_desc-xcp_quality.tsv \
        cpac_RBCv0/sub-*/ses-*/func/*desc-FDJenkinson_motion.1D
    ```


    Parameters:
    -----------

    study_name : str
        Name of the RBC study being concatenated

    bold_dir : pathlib.Path
        root path of the CPAC dataset


    """
    logging.info("Finding xcp-quality files")
    qc_files = list(
        bold_dir.glob(
            "cpac_RBCv0/sub-*/ses-*/func/*reg-36Parameter_desc-xcp_quality.tsv"
        )
    )
    logging.info(f"found {len(qc_files)} qc files")
    qc_dfs = []
    for qc_file in tqdm(qc_files):
        qc_df = pd.read_csv(qc_file, sep="\t")
        qc_df.drop(["sub", "ses"], axis=1, inplace=True)
        entities = dict(
            [
                part.split("-")
                for part in qc_file.name.replace("_quality.tsv", "").split("_")
            ]
        )
        qc_df["participant_id"] = entities["sub"]
        qc_df["acq"] = entities.get("acq")
        qc_df["task"] = entities.get("task")
        # Be certain they're strings
        qc_df["run"] = entities.get("run", "")
        qc_df["session_id"] = entities["ses"]
        qc_dfs.append(qc_df)
        qc_df["medianFD"] = get_jenkinson_fd(qc_file)
    all_qc = pd.concat(qc_dfs, axis=0, ignore_index=True)

    # what should be excluded based on the QC scores?
    all_qc["normCrossCorrExclude"] = np.where(all_qc["normCrossCorr"] <= 0.8, 1, 0)
    all_qc["motionExclude"] = np.where(all_qc["medianFD"] >= 0.2, 1, 0)
    all_qc["fmriExclude"] = np.where(
        all_qc["motionExclude"] + all_qc["normCrossCorrExclude"] > 0, 1, 0
    )

    output_file = bold_dir / "cpac_RBCv0" / f"study-{study_name}_desc-functional_qc.tsv"
    logging.info(f"writing bold qc tsv to {output_file}")
    all_qc.to_csv(output_file, index=False, sep="\t")


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "study_name",
        choices=["CCNP", "BHRC", "NKI", "HBN", "PNC", "HCPD"],
        help="Which RBC study are you working with",
    )
    parser.add_argument(
        "--bold-dir", type=Path, help="Path to the study's CPAC derivative dataset"
    )
    parser.add_argument("--quiet", action="store_true", default=False)
    return parser


if __name__ == "__main__":
    args = get_parser().parse_args()
    if not args.quiet:
        logging.basicConfig(level=logging.INFO)

    if args.bold_dir.exists():
        concatenate_bold_qc(args.study_name, args.bold_dir)
