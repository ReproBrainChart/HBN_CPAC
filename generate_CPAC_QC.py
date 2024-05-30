import numpy as np 
import os
import pandas as pd
import glob
import sys
study = sys.argv[1]
study_path = study+"_CPAC"
print('The path is ' + study_path)
files = os.path.join("/cbica/projects/RBC/QC_Concatenation",study_path,
"cpac_RBCv0/sub*/ses*/func","*36*xcp*sv")
files = glob.glob(files)
num = len(files)
print('The number of files is '+str(num))
df_list=[]

for file in files:
        df = pd.read_table(file)
        median_file = file.split("space")[0]+"*desc-FDJenkinson_motion.1D"
        median_file = glob.glob(median_file)
        try:
                df["medianFD"]=(pd.DataFrame.median(pd.read_table(median_file[0])))[0]
        except:
                os.system('datalad get'+median_file[0])
                df["medianFD"]=(pd.DataFrame.median(pd.read_table(median_file[0])))[0]                
        df_list.append(df)


df = pd.concat(df_list, ignore_index=True)
num = len(df)
df["motionExclude"]=pd.DataFrame(np.zeros(df.shape[0])).astype(int)
df["normCrossCorrExclude"]=pd.DataFrame(np.zeros(df.shape[0])).astype(int)
df["fmriExclude"]=pd.DataFrame(np.zeros(df.shape[0])).astype(int)
df["motionExclude"][df["medianFD"]>=0.2]=1
df["normCrossCorrExclude"][df["normCrossCorr"]<=0.8]=1
df["fmriExclude"][df["normCrossCorrExclude"]==1]=1
df["fmriExclude"][df["motionExclude"]==1]=1
combined_df=df.rename(columns={"sub": "participant_id", "ses": "session_id"})


print('The number of runs in this .csv is '+str(num))
path = '/cbica/projects/RBC/QC_Concatenation/'+str(study_path)+'/cpac_RBCv0/study-'+study+'_desc-functional_qc.tsv'
print ('The path to the csv is '+str(path))
combined_df.to_csv(path,sep="\t",index=False)
