datalad run -i "cpac_RBCv0/sub*/ses*/func/*36*xcp*sv" -o "study-HBN_desc-functional_qc.tsv" --expand inputs --explicit "python generate_CPAC_QC.py HBN"
