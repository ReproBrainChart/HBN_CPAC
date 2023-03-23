#!/bin/bash
set -e -u -x

subid="$1"
sesid="$2"

# Create a filter file that only allows this session
filterfile=${PWD}/${sesid}_filter.json
echo "{" > ${filterfile}
echo "'fmap': {'datatype': 'fmap'}," >> ${filterfile}
echo "'bold': {'datatype': 'func', 'session': '$sesid', 'suffix': 'bold'}," >> ${filterfile}
echo "'sbref': {'datatype': 'func', 'session': '$sesid', 'suffix': 'sbref'}," >> ${filterfile}
echo "'flair': {'datatype': 'anat', 'session': '$sesid', 'suffix': 'FLAIR'}," >> ${filterfile}
echo "'t2w': {'datatype': 'anat', 'session': '$sesid', 'suffix': 'T2w'}," >> ${filterfile}
echo "'t1w': {'datatype': 'anat', 'session': '$sesid', 'suffix': 'T1w'}," >> ${filterfile}
echo "'roi': {'datatype': 'anat', 'session': '$sesid', 'suffix': 'roi'}" >> ${filterfile}
echo "}" >> ${filterfile}

# remove ses and get valid json
sed -i "s/'/\"/g" ${filterfile}
sed -i "s/ses-//g" ${filterfile}

mkdir -p ${subid}_${sesid}_outputs
# C-PAC-specific memory optimization -----------------------------
if [[ -f code/runtime_callback.log ]]
then
  singularity run --cleanenv \
      -B ${PWD} \
      -B ${PWD}/${subid}_${sesid}_outputs:/outputs \
      pennlinc-containers/.datalad/environments/cpac-1-8-5/image \
      inputs/data \
      /outputs \
      participant \
      --preconfig rbc-options \
      --skip_bids_validator \
      --n_cpus 4 \
      --mem_gb 32 \
      --participant_label "$subid" \
      --runtime_usage=code/runtime_callback.log \
      --runtime_buffer=30
# ----------------------------------------------------------------
else
  singularity run --cleanenv \
      -B ${PWD} \
      -B ${PWD}/${subid}_${sesid}_outputs:/outputs \
      pennlinc-containers/.datalad/environments/cpac-1-8-5/image \
      inputs/data \
      /outputs \
      participant \
      --preconfig rbc-options \
      --skip_bids_validator \
      --n_cpus 4 \
      --mem_gb 32 \
      --participant_label "$subid"
fi

rm -rf ${subid}_${sesid}_outputs/working
7z a ${subid}_${sesid}_c-pac-1.8.5.zip ${subid}_${sesid}_outputs
rm -rf ${subid}_${sesid}_outputs
rm ${filterfile}

