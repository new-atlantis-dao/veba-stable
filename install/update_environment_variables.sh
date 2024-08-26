#!/bin/bash
# __version__ = "2024.6.6"
# usage: bash veba/update_environment_variables.sh /path/to/veba_database_destination/ [optional positional argument: /path/to/conda_environments/]

# Create database
DATABASE_DIRECTORY=${1:-"."}
REALPATH_DATABASE_DIRECTORY=$(realpath $DATABASE_DIRECTORY)

CONDA_ENVS_PATH=${2:-"$(conda info --base)/envs/"}

# CONDA_BASE=$(conda run -n base bash -c "echo \${CONDA_PREFIX}")

echo ". .. ... ..... ........ ............."
echo " * Adding the following environment variable to VEBA environments: export VEBA_DATABASE=${REALPATH_DATABASE_DIRECTORY}"

# VEBA
for ENV_PREFIX in ${CONDA_ENVS_PATH}/VEBA-*; do 
    echo $ENV_PREFIX;
    mkdir -v -p ${ENV_PREFIX}/etc/conda/activate.d/
    mkdir -v -p ${ENV_PREFIX}/etc/conda/deactivate.d/
    echo "export VEBA_DATABASE=${REALPATH_DATABASE_DIRECTORY}" > ${ENV_PREFIX}/etc/conda/activate.d/veba.sh
    echo "unset VEBA_DATABASE" > ${ENV_PREFIX}/etc/conda/deactivate.d/veba.sh
    done

# CheckM2
echo ". .. ... ..... ........ ............."
echo " * Adding the following environment variable to VEBA environments: export CHECKM2DB=${REALPATH_DATABASE_DIRECTORY}/Classify/CheckM2/uniref100.KO.1.dmnd"
for ENV_NAME in VEBA-binning-prokaryotic_env; do 
    ENV_PREFIX=${CONDA_ENVS_PATH}/${ENV_NAME}
    # CheckM2
    echo "export CHECKM2DB=${REALPATH_DATABASE_DIRECTORY}/Classify/CheckM2/uniref100.KO.1.dmnd" >> ${ENV_PREFIX}/etc/conda/activate.d/veba.sh
    echo "unset CHECKM2DB" >> ${ENV_PREFIX}/etc/conda/deactivate.d/veba.sh    
    done 

# GTDB
echo ". .. ... ..... ........ ............."
echo " * Adding the following environment variable to VEBA environments: export GTDBTK_DATA_PATH=${REALPATH_DATABASE_DIRECTORY}/Classify/GTDB/"
for ENV_NAME in VEBA-classify-prokaryotic_env; do 
    ENV_PREFIX=${CONDA_ENVS_PATH}/${ENV_NAME}
    # GTDB
    echo "export GTDBTK_DATA_PATH=${REALPATH_DATABASE_DIRECTORY}/Classify/GTDB/" >> ${ENV_PREFIX}/etc/conda/activate.d/veba.sh
    echo "unset GTDBTK_DATA_PATH" >> ${ENV_PREFIX}/etc/conda/deactivate.d/veba.sh
    done 

# CheckV
echo ". .. ... ..... ........ ............."
echo " * Adding the following environment variable to VEBA environments: export CHECKVDB=${REALPATH_DATABASE_DIRECTORY}/Classify/CheckV/"
for ENV_NAME in VEBA-binning-viral_env; do 
    ENV_PREFIX=${CONDA_ENVS_PATH}/${ENV_NAME}
    echo "export CHECKVDB=${REALPATH_DATABASE_DIRECTORY}/Classify/CheckV" >> ${ENV_PREFIX}/etc/conda/activate.d/veba.sh
    echo "unset CHECKVDB" >> ${ENV_PREFIX}/etc/conda/deactivate.d/veba.sh
    done

echo -e " _    _ _______ ______  _______\n  \  /  |______ |_____] |_____|\n   \/   |______ |_____] |     |"
echo -e ".........................................."
echo -e "  Setting Environment Variable Complete   "
echo -e ".........................................."
echo -e "The VEBA database environment variable is set in your VEBA conda environments: \n\tVEBA_DATABASE=${REALPATH_DATABASE_DIRECTORY}"