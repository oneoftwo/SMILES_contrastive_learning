#!/bin/bash
#PBS -N LJW_PP
#PBS -l nodes=gnode9:ppn=4
#PBS -l walltime=1000:00:00

cd $PBS_O_WORKDIR
echo `cat $PBS_NODEFILE`
cat $PBS_NODEFILE
NPROCS=`wc -l < $PBS_NODEFILE`

exp_name=pp_L

source activate LJW_DeepSLIP
source activate LJW_add
rm -rf ./save/${exp_name}/ 
mkdir ./save/${exp_name}/ 

python -u train_siam.py \
--data_fn ./data/PubChem/PubChem_1000000.pkl \
--save_dir ./save/${exp_name}/ \
--hid_dim 256 \
--n_layer 3 \
--bs 512 \
--lr 1e-6 \
--n_epoch 1000 \
--no_use_siam \
--use_pp_prediction \
1>./save/${exp_name}/output.txt \
2>./save/${exp_name}/error.txt

