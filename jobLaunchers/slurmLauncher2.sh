#!/bin/bash
#SBATCH -N 1 
#SBATCH -p RM-shared
#SBATCH --ntasks-per-node 2
#SBATCH -t 0:05:00 # ~ 52:00:00 (HH:MM:SS) for unparallelized
#SBATCH --mail-user=jmschabdach@gmail.com

# echo commands to stdout
set -x

echo "$@"
"$@"
