#!/usr/bin/env bash

# to manually nuke the current miniconda install
# rm -rf ~/miniconda3 ~/.condarc ~/.conda ~/.continuum ~/.jupyter ~/.ipython ~/.local/share/jupyter/ ~/Library/Jupyter

# make a Downloads folder
{
if [ ! -d "$HOME/Downloads" ]; then
    mkdir -p "$HOME/Downloads"
fi
}

MC_DIR="miniconda3"
MC_DL_FILE="Miniconda3-latest-Linux-x86_64.sh"
MC_DL_PATH="$HOME/Downloads/$MC_DL_FILE"
MC_DIR_PATH="$HOME/$MC_DIR"

# # Exit if miniconda file already exists
# {
# if [ -f "$MC_DL_PATH" ]; then
#     echo "$MC_DL_PATH already exists! Delete before running this script to ensure installation is up-to-date."
#     exit 0
# fi
# }

# Download miniconda file only if it does not already exist
{
if [ ! -f "$MC_DL_PATH" ]; then
    wget --show-progress -O $MC_DL_PATH https://repo.continuum.io/miniconda/$MC_DL_FILE
fi
}

# install
bash $MC_DL_PATH -b -p $MC_DIR_PATH

# Add to and source .bashrc
export PATH="$MC_DIR_PATH/bin:$PATH"
# Clears history
hash -r

# -q for quiet
conda update -q conda -y

conda install -n base _license -y

conda upgrade --all -y

# enable usage of conda command
. $HOME/$MC_DIR/etc/profile.d/conda.sh

conda activate base

# Install dependencies
conda env update -f environment.yml

# Install the CMU dictionary
python -c "import nltk; nltk.download('cmudict')"

# add "conda activate" to ~/.bash_profile, enable using it for other envs
echo '' >> ~/.bash_profile
echo '# enable conda activate' >> ~/.bash_profile
echo '. $HOME/'$MC_DIR'/etc/profile.d/conda.sh' >> ~/.bash_profile
echo '# activate the base environment' >> ~/.bash_profile
echo 'conda activate' >> ~/.bash_profile
