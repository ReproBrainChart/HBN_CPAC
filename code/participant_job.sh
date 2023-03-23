#!/bin/bash
#$ -S /bin/bash
#$ -l h_vmem=32G
#$ -l s_vmem=32G
#$ -l tmpfree=200G
# Set up the correct conda environment
source ${CONDA_PREFIX}/bin/activate base
echo I\'m in $PWD using `which python`

# fail whenever something is fishy, use -x to get verbose logfiles
set -e -u -x

# Set up the remotes and get the subject id from the call
dssource="$1"
pushgitremote="$2"
subid="$3"
sesid="$4"

# change into the cluster-assigned temp directory. Not done by default in SGE
cd ${CBICA_TMPDIR}
# OR Run it on a shared network drive
# cd /cbica/comp_space/$(basename $HOME)

# Used for the branch names and the temp dir
BRANCH="job-${JOB_ID}-${subid}-${sesid}"
mkdir ${BRANCH}
cd ${BRANCH}

# get the analysis dataset, which includes the inputs as well
# importantly, we do not clone from the lcoation that we want to push the
# results to, in order to avoid too many jobs blocking access to
# the same location and creating a throughput bottleneck
datalad clone "${dssource}" ds

# all following actions are performed in the context of the superdataset
cd ds

# in order to avoid accumulation temporary git-annex availability information
# and to avoid a syncronization bottleneck by having to consolidate the
# git-annex branch across jobs, we will only push the main tracking branch
# back to the output store (plus the actual file content). Final availability
# information can be establish via an eventual `git-annex fsck -f joc-storage`.
# this remote is never fetched, it accumulates a larger number of branches
# and we want to avoid progressive slowdown. Instead we only ever push
# a unique branch per each job (subject AND process specific name)
git remote add outputstore "$pushgitremote"

# all results of this job will be put into a dedicated branch
git checkout -b "${BRANCH}"

# we pull down the input subject manually in order to discover relevant
# files. We do this outside the recorded call, because on a potential
# re-run we want to be able to do fine-grained recomputing of individual
# outputs. The recorded calls will have specific paths that will enable
# recomputation outside the scope of the original setup
datalad get -n "inputs/data/${subid}"

# Reomve all subjects we're not working on
(cd inputs/data && rm -rf `find . -type d -name 'sub*' | grep -v $subid`)

# ------------------------------------------------------------------------------
# Do the run!

# C-PAC-specific memory optimization --------------------------------
if [[ -f code/runtime_callback.log ]]
then
  datalad run \
      -i code/c-pac_zip.sh \
      -i code/runtime_callback.log \
      -i inputs/data/${subid}/${sesid} \
      -i inputs/data/*json \
      -i pennlinc-containers/.datalad/environments/cpac-1-8-5/image \
      --explicit \
      -o ${subid}_${sesid}_c-pac-1.8.5.zip \
      -m "C-PAC:1.8.5 ${subid} ${sesid}" \
      "bash ./code/c-pac_zip.sh ${subid} ${sesid}"
# -------------------------------------------------------------------
else
  datalad run \
      -i code/c-pac_zip.sh \
      -i inputs/data/${subid} \
      -i inputs/data/*json \
      -i pennlinc-containers/.datalad/environments/cpac-1-8-5/image \
      --explicit \
      -o ${subid}_${sesid}_c-pac-1.8.5.zip \
      -m "C-PAC:1.8.5 ${subid}" \
      "bash ./code/c-pac_zip.sh ${subid}"
fi

# file content first -- does not need a lock, no interaction with Git
datalad push --to output-storage
# and the output branch
flock $DSLOCKFILE git push outputstore

# remove tempdir
echo TMPDIR TO DELETE
echo ${BRANCH}

datalad uninstall -r --nocheck --if-dirty ignore inputs/data
datalad drop -r . --nocheck
git annex dead here
cd ../..
rm -rf $BRANCH

echo SUCCESS
# job handler should clean up workspace
