#!/bin/bash
#SBATCH -N 1 
#SBATCH -p RM-shared
#SBATCH --ntasks-per-node 2
#SBATCH -t 0:10:00 # ~ 52:00:00 (HH:MM:SS) for unparallelized

# echo commands to stdout
set -x

echo "$@"
"$@"
