# shellcheck shell=bash
# shellcheck disable=SC2034  # read by _common.sh after sourcing
# Connection settings for the deploy/aws scripts.  Copy this file to aws_env.sh (which is
# git-ignored) and fill in the values.  Nothing secret goes in here: only host names, the
# login user and the PATHS of the key file and the licence file.  The key and the licence
# themselves stay where they are; the scripts read the paths and pass the files to ssh / scp
# without printing them.
#
#   cp deploy/aws/aws_env.example.sh deploy/aws/aws_env.sh
#   chmod 600 deploy/aws/aws_env.sh
#
# The same variables can be exported in the shell instead of using the file.

# Public IPv4 DNS or public IPv4 address of the instance
# (EC2 console -> Instances -> select the instance -> "Public IPv4 DNS"; README_AWS.md section 5).
# It changes after every stop/start unless an Elastic IP is attached.
AWS_HOST="ec2-3-0-0-0.us-east-2.compute.amazonaws.com"

# Login user of the Ubuntu Server 24.04 AMI (always "ubuntu" for that image).
AWS_USER="ubuntu"

# Path of the private key (.pem) downloaded when the key pair was created (README section 3).
# Keep it in ~/.ssh with mode 400:  chmod 400 ~/.ssh/battery-swap.pem
AWS_KEY="$HOME/.ssh/battery-swap.pem"

# Region of the instance (Ohio).  Informational for the scripts; used in the README commands.
AWS_REGION="us-east-2"

# Project root on the instance.  The layout under it mirrors the local "OR Model-Battery Swap"
# folder: ebike_swap_sim/ (package, experiments, tests, outputs), data/, notes/data/, deploy/aws/.
AWS_REMOTE_ROOT="/home/ubuntu/battery_swap"

# Local PATH of the Gurobi WLS licence file (the file downloaded from the Gurobi Web License
# Manager; usually named gurobi.lic).  upload_licence.sh copies it to ~/gurobi/gurobi.lic on
# the instance with mode 600.  The file is never read by the scripts, never printed and never
# synced by sync_up.sh (*.lic is excluded).
GRB_LICENSE_LOCAL="$HOME/Desktop/gurobi.lic"

# Where sync_down.sh puts the results by default (a mirror beside the real outputs/, so that a
# download never overwrites records the laptop is still writing).  --in-place writes into
# ebike_swap_sim/outputs/ instead.
LOCAL_RESULTS_DIR="cloud_results"

# Optional: ssh port (22 unless you changed the security group rule).
AWS_SSH_PORT="22"
