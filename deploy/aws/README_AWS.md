# Running the round-6 experiments on AWS EC2 (us-east-2, Ohio)

A step-by-step guide for a first-time AWS user whose console is displayed in Chinese.
Every console item is given in English with the Chinese menu name in parentheses, e.g.
Launch instance. The scripts in this folder do the copying and the running; you do
the account-side clicks (quota, key pair, instance, licence, budget) once.

Everything is designed so that **no secret ever enters the repository**: the key file stays in
`~/.ssh`, the Gurobi licence stays on the Desktop and goes to the server with `scp`, and the
only file you fill in (`aws_env.sh`) holds host names and file *paths*. `aws_env.sh` and `*.lic`
are in `.gitignore`.

## 0. What you get, in one picture

```
laptop (OR Model-Battery Swap/)                       EC2 instance (/home/ubuntu/battery_swap/)
  ebike_swap_sim/{ebike_swap_sim,experiments,tests}   ----sync_up.sh---->   same layout
  data/, food_order.csv, notes/data/                  ----sync_up.sh---->   same layout
  ebike_swap_sim/outputs/{r6_penalty,r6_fill,r6_o2}   ----sync_up.sh---->   resumable records
  ~/Desktop/gurobi.lic                                --upload_licence.sh-> ~/gurobi/gurobi.lic (600)
                                                      bootstrap.sh: apt, venv, pip, licence check,
                                                                    toy ILP = 12.5, smoke stage
                                                      make_cloud_lanes.py -> outputs/cloud_lanes/lanes.txt
                                                      run_lanes.sh start   -> one tmux session per lane
  cloud_results/ebike_swap_sim/outputs/...            <---sync_down.sh----  records, tables, figures
```

Files in `deploy/aws/`:

| File | Where it runs | Purpose |
|---|---|---|
| `aws_env.example.sh` | laptop | template of the connection file; copy to `aws_env.sh` (git-ignored) |
| `requirements.txt` | server | Python packages pinned to the laptop's versions, CPU-only torch |
| `sync_up.sh` | laptop | rsync code + data + resumable outputs to the server (`--dry-run` first) |
| `upload_licence.sh` | laptop | scp the Gurobi WLS licence to `~/gurobi/gurobi.lic`, mode 600 |
| `bootstrap.sh` | server | one-time setup and the three checks (licence, toy optimum 12.5, smoke stage) |
| `make_cloud_lanes.py` | server | writes `lanes.txt`: the remaining stages, one per lane |
| `run_lanes.sh` | server | start / status / stop / logs of the lanes in tmux with thread accounting |
| `rewrite_paths.py` | server | fixes laptop paths stored in the siting caches (called by bootstrap) |
| `sync_down.sh` | laptop | rsync the results back (into `cloud_results/` by default) |
| `_common.sh` | laptop | shared helper sourced by the laptop scripts |

## 1. Before you start: region and language

* Region: the console must show **US East (Ohio) us-east-2** in the
  top-right region menu. Instances, key pairs, security groups and quotas are per region; the
  instance you launch must be in the same region as the key pair.
* The console language (Chinese) does not change any command in this guide. If you prefer English
  temporarily: account menu (top right) -> Settings -> Language.
* Account id, key files, licence files: never paste them into chat, notes or git.

## 2. Service Quotas: check and raise the vCPU limit

New accounts usually may run only a handful of vCPUs. The target instance has 32 vCPUs, so the
limit must be raised **before** launching; the request is free and usually approved within
minutes to two days.

1. Search "Service Quotas" in the top search bar and open it.
2. Left menu: AWS services -> search "EC2" -> Amazon Elastic Compute Cloud (Amazon EC2).
3. Find these two quotas (use the search box in the quota list):
   * **Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances**.
     The value is in **vCPUs**, not instances.
   * **All Standard (A, C, D, H, I, M, R, T, Z) Spot Instance Requests**,
     also in vCPUs.
4. Click the quota -> Request increase at account level -> enter the
   new value: **64** for both (room for one r7i.8xlarge plus a small helper instance) -> Request.
   A reason in English such as "Academic operations-research experiments (Gurobi MIP), batch
   workload, 32 vCPU instance" helps.
5. Track it under Quota request history. Until the increase is granted you can
   still launch an instance that fits the current limit (e.g. r7i.2xlarge = 8 vCPUs), set it up and
   stop it; see 4.4 "change instance type".

If a launch fails with `VcpuLimitExceeded`, this quota is the reason.

## 3. Key pair

1. EC2 console -> left menu Network & Security -> Key Pairs -> Create key
   pair.
2. Name: `battery-swap`; type: ED25519 (or RSA); file format: **.pem**. Create -- the
   browser downloads `battery-swap.pem` once. It cannot be downloaded again.
3. On the laptop:
   ```bash
   mkdir -p ~/.ssh && mv ~/Downloads/battery-swap.pem ~/.ssh/ && chmod 400 ~/.ssh/battery-swap.pem
   ```
   Never commit it; never paste it anywhere. The scripts only use its *path* (`AWS_KEY`).

## 4. Launch the instance

EC2 console -> Instances -> Launch instances.

### 4.1 Name and image
* Name: `battery-swap-r6`.
* Application and OS Images -> Quick Start
  -> **Ubuntu** -> AMI: **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type**, architecture **64-bit (x86)**.
  Not Arm: the pinned wheels are x86_64.

### 4.2 Instance type and prices
Recommendations for us-east-2 (Linux, approximate on-demand list prices as of late 2026; the
console shows the exact figure next to the type as "On-Demand Linux base pricing";
Spot prices move hourly and are typically 30-45 % of on-demand):

| Type | vCPU / RAM | On-demand ≈ | Spot ≈ | Use |
|---|---|---|---|---|
| r7i.2xlarge | 8 / 64 GB | 0.53 USD/h | 0.20-0.30 | first small step while the quota is low: bootstrap, 2 lanes |
| r7i.4xlarge | 16 / 128 GB | 1.06 USD/h | 0.40-0.55 | 4 lanes at Threads 3 by default (5 with `--max-threads 15`) |
| **r7i.8xlarge** | **32 / 256 GB** | **2.12 USD/h** | **0.80-1.10** | target: 8 lanes at Threads 3 by default, or 4 beside the 11-thread siting pass; 10 lanes with `--max-threads 31` |
| m7i.8xlarge | 32 / 128 GB | 1.61 USD/h | 0.60-0.85 | cheaper alternative with enough memory (the laptop runs the siting pass in about 7 GB and a lane in 1-2 GB) |
| c7i.8xlarge | 32 / 64 GB | 1.43 USD/h | 0.55-0.75 | cheapest 16-core option; 64 GB still covers the whole round-6 plan (about 30 GB) |

**vCPUs are hyperthreads.** Every type above has half as many physical cores as vCPUs
(r7i.8xlarge: 16 cores). Gurobi gains little from the second hyperthread of a core, and the lane
timings in `lanes.json` were measured on the laptop with 3 threads on physical cores. So
`run_lanes.sh` runs **1.5 solver threads per core** by default (24 threads on r7i.8xlarge = 8
lanes). `--max-threads 31` runs ten lanes, each slower, which matters for the retry lanes whose
purpose is to reach OPTIMAL within a time limit; `--max-threads 16` is the conservative setting.

A full round-6 catch-up (the longest lanes are the O2 siting pass, about 8 h, and the psweep /
levers retries, about 4 h) is roughly one day on r7i.8xlarge with the default 8 lanes: about 50
USD on-demand, about 20-25 USD on Spot, plus about 16 USD per month for the 200 GB volume while
it exists. Treat the lane minutes in `lanes.json` as lower bounds on the server.

Memory need: about 30 GB in total for 8-10 lanes plus the siting pass, so every type above is safe.

### 4.3 Key pair, network, storage
* Key pair: select `battery-swap`.
* Network settings -> Edit is not needed; keep the default VPC and subnet, Auto-assign
  public IP **Enable**.
* Firewall / security group: **Create security group**, name
  `battery-swap-ssh`, and tick **Allow SSH traffic from** ->
  **My IP**. Nothing else is opened. Outbound stays "all" (the Gurobi WLS licence and
  `apt`/`pip` need outbound HTTPS). When your laptop's public IP changes (new network), edit the
  inbound rule: Security Groups -> battery-swap-ssh -> Edit inbound rules
  -> Source -> My IP.
* Configure storage: **200 GiB, gp3** (root volume). 3000 IOPS / 125 MB/s defaults are
  fine. Keep "Delete on termination" ticked only if you accept that Terminate deletes
  the data; results are synced back anyway.

### 4.4 On-demand first, Spot later (and how to grow)
* **Simplest path**: launch **on-demand** r7i.2xlarge now (fits a small quota), run the setup of
  Sections 6-8, then Stop it. Once the quota is raised: Instance state -> Stop,
  then Actions -> Instance settings -> **Change instance type** ->
  r7i.8xlarge -> Start. The disk, venv, data and outputs are all kept; only the public IP changes.
* **Spot** saves 55-70 % but can be interrupted with a 2-minute warning. In the launch
  form: Advanced details -> Purchasing option -> **Request Spot Instances**
  -> Customize: Request type **Persistent**, Interruption
  behavior **Stop**. With these two settings an interrupted instance is stopped, not
  destroyed, and AWS restarts it when capacity returns; `run_lanes.sh start` then resumes every
  lane (Section 10). An on-demand instance cannot be converted to Spot; instead Actions ->
  Image and templates -> Create image of the bootstrapped on-demand instance
  and launch the Spot instance from that AMI.

Click **Launch instance**. After about a minute the instance shows "Running"
with a Public IPv4 DNS such as `ec2-3-xx-xx-xx.us-east-2.compute.amazonaws.com`.

## 5. Connect by SSH

```bash
ssh -i ~/.ssh/battery-swap.pem ubuntu@ec2-3-xx-xx-xx.us-east-2.compute.amazonaws.com
```
The user is always `ubuntu` on the Ubuntu AMI. Answer `yes` to the first host-key question. The
console's Connect button shows the same command. If you see `Permission denied (publickey)`,
check the key path, `chmod 400`, the user name and that the instance uses that key pair.

The public address changes after every Stop/Start. Either update `AWS_HOST` in `aws_env.sh`
each time, or allocate an Elastic IP: Network & Security -> Elastic IPs
 -> Allocate -> Actions -> Associate with the
instance. Any public IPv4 address costs about 3.6 USD per month (0.005 USD/h) while in use, the
auto-assigned one included; an Elastic IP costs the same while the instance runs and **keeps
billing while the instance is stopped or the address is unattached**, so release it (Release)
when the project ends.

## 6. Laptop side: connection file and first upload

```bash
cd "/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap"
cp deploy/aws/aws_env.example.sh deploy/aws/aws_env.sh && chmod 600 deploy/aws/aws_env.sh
# edit deploy/aws/aws_env.sh: AWS_HOST, AWS_KEY, GRB_LICENSE_LOCAL (paths only)
deploy/aws/sync_up.sh --dry-run      # lists what would be sent (about 105 MB the first time:
                                     # 27 MB code + data, 75 MB resumable outputs, 3,200 files)
deploy/aws/sync_up.sh                # code, data, notes/data, deploy/aws, resumable outputs
```
What is sent and what is never sent is listed at the top of `sync_up.sh`. A second run only
transfers changes (rsync, compressed, resumable). `--code-only` after editing code, `--outputs-only`
to refresh records.

## 7. Gurobi WLS academic licence

The laptop's academic licence is machine-bound and cannot be copied. The **Web License Service
(WLS)** academic licence works on any machine with internet access: create it in the Gurobi Web
License Manager (portal.gurobi.com -> Licenses -> Request -> WLS Academic), download `gurobi.lic`
to the Desktop, and never open or paste it.

```bash
deploy/aws/upload_licence.sh                 # uses GRB_LICENSE_LOCAL from aws_env.sh
# or: deploy/aws/upload_licence.sh ~/Desktop/gurobi.lic
```
The script copies the file to `~/gurobi/gurobi.lic` on the server with mode 600 and prints only
its size. `bootstrap.sh` writes `export GRB_LICENSE_FILE=$HOME/gurobi/gurobi.lic` into
`~/battery_swap/env.sh`, which every lane sources. The licence check in `bootstrap.sh` only
confirms that gurobipy can start and solve a one-variable model; Gurobi's banner (licence id,
registered e-mail) is discarded so it never appears in a log. WLS needs outbound HTTPS to Gurobi's
servers (the default security group allows it). Keep the licence out of every sync: `*.lic` is
excluded by the scripts and ignored by git.

## 8. Server side: bootstrap

Run it inside tmux on the server, so that a sleeping laptop or a dropped Wi-Fi does not kill the
`pip install` half-way, and keep a log:

```bash
ssh -t -i ~/.ssh/battery-swap.pem ubuntu@<host> \
  'tmux new -A -s boot "bash ~/battery_swap/deploy/aws/bootstrap.sh 2>&1 | tee ~/bootstrap.log; echo; echo finished -- press Enter; read -r"'
```
(tmux is preinstalled on the Ubuntu Server AMI; if `tmux: command not found`, run
`sudo apt-get install -y tmux` once.) If the connection drops, ssh in again and
`tmux attach -t boot`; the full output is in `~/bootstrap.log`. The script is idempotent (it
reuses the venv and repeats pip and the checks), so simply re-run it after any interruption.

About 5-8 minutes. It installs apt packages (python3.12-venv, tmux, rsync, htop, ...), creates
`~/battery_swap/venv`, installs `requirements.txt` (CPU torch, about 190 MB), writes `env.sh`,
and runs three checks, each reported as `OK` or `FAIL` in the summary. On an instance booted
less than about five minutes earlier, Ubuntu's automatic updater may still hold the apt lock;
`bootstrap.sh` waits for it (up to 10 min), and if apt still fails it stops and asks you to re-run
it two minutes later.

1. **Licence**: gurobipy created and solved a model under `GRB_LICENSE_FILE`.
2. **Toy invariant**: the aggregated toy ILP optimum equals **12.5** (pytest
   `tests/test_aggregate.py::test_toy_12_5_11_2_106_aggregated` plus a direct check at Threads 1).
3. **Smoke stage**: `experiments/r6_penalty.py --stage psweep --smoke --threads 1` (about 30-60 s)
   into `~/battery_swap/scratch/smoke` (not into `outputs/`).

Then it rewrites the laptop paths stored in the siting caches (`rewrite_paths.py`). Options:
`--run-tests` adds the whole pytest suite (about 390 tests), `--checks-only` repeats the checks
(e.g. after re-uploading a licence), `--skip-apt`.

## 9. Run the lanes

```bash
ssh -i ~/.ssh/battery-swap.pem ubuntu@<host>
. ~/battery_swap/env.sh                                  # venv, GRB_LICENSE_FILE, cd ebike_swap_sim
python3 ../deploy/aws/make_cloud_lanes.py                # -> outputs/cloud_lanes/lanes.txt (+ lanes.json)
less outputs/cloud_lanes/lanes.txt                       # one lane per remaining stage; comments explain
bash ../deploy/aws/run_lanes.sh start outputs/cloud_lanes/lanes.txt --dry-run
bash ../deploy/aws/run_lanes.sh start outputs/cloud_lanes/lanes.txt
bash ../deploy/aws/run_lanes.sh status outputs/cloud_lanes/lanes.txt
```

* `make_cloud_lanes.py` reads the records on the server and writes one lane per remaining
  stage: the `r6_fill --retry-unsolved` re-solves (only for stages that still have unsolved rows),
  the new `r6_fill` stages (transfers, stress, rolling_ext, pack, levers_ext, compliance; a stage
  with a `RESULTS.md` is listed as finished), the O2 siting second pass (`--o2 auto|force|none`),
  a final analysis lane, and commented placeholders for the planned O3-O5 runs. Threads: 3 per r6
  lane (the R6 protocol), 11 for the siting pass, 1 for the analysis. On 32 vCPUs (16 cores) the
  dispatcher runs eight r6 lanes at once by default, or four beside the siting pass (Section 4.2;
  `--max-threads 31` for ten). The header of `lanes.txt` says which O2 pass and layout the
  compliance stage will use and whether that result is certified.
  If the siting pass is still running on the laptop and you want the server to leave it alone:
  `--o2 none` (compliance then uses the written m = 2 layout already in the records).
* `run_lanes.sh start` writes a wrapper per lane, starts a dispatcher in the tmux session
  `lanes_dispatch`, and the dispatcher launches lanes (one tmux session `lane_<name>` each) while
  the sum of their threads stays at or below 1.5 x physical cores (`--max-threads N` to change;
  the `--dry-run` plan prints the budget and the cores it found). Lanes with dependencies
  (`after`) wait until those lanes finished **successfully**. `--only a,b` runs a subset.
* Watch: `run_lanes.sh status`, `run_lanes.sh logs r6_stress 60`, `htop`, or
  `tmux attach -t lane_r6_stress` (detach with `Ctrl-b` then `d`; never `Ctrl-c` inside, that kills
  the solve). Status files: `outputs/cloud_lanes/lane_<name>.status` (START / EXIT rc / lane DONE
  with UTC times), logs `lane_<name>.log`.
* Stop: `run_lanes.sh stop r6_stress` terminates that lane's processes and puts the lane **on
  hold** (the dispatcher will not restart it); `run_lanes.sh stop all` stops the dispatcher and
  every lane. The next explicit `run_lanes.sh start` releases held lanes, and every lane resumes
  from its records. Status states: `queued`, `running`, `done` (exit code 0), `failed (rc=N)`,
  `blocked` (a lane it depends on failed), `on hold`, `released`, `interrupted` (was running when
  the machine stopped; `start` restarts it).
* **A lane that exits with an error** (out of memory, Gurobi error 10009, a wrong flag) shows as
  `failed (rc=N)`; the dispatcher does not retry it and holds back the lanes that depend on it
  (compliance waits for the siting lane, the final analysis waits for every r6 lane), so nothing
  runs on incomplete records. Read `run_lanes.sh logs <name>`, fix the cause, then run
  `run_lanes.sh start outputs/cloud_lanes/lanes.txt` again: it releases the failed (and held)
  lanes, and if a dispatcher is still running it simply picks them up within 30 s. When all other
  lanes are finished the dispatcher exits and `dispatcher.log` lists the failed lanes.

You can close the laptop: tmux keeps everything running on the server.

### 9.1 R7 siting production lanes (r7i.4xlarge, `notes/siting_production_plan.md` 2.1 / 2.2)

```bash
# laptop: (re)write the plan, then sync_up.sh as usual
cd ebike_swap_sim && PYTHONPATH=. python3 experiments/r7_search.py --write-lanes
# server (project root). First make sure the step-2b probe is no longer running:
tmux ls                                              # no 'probe' session
tail -n 1 ebike_swap_sim/outputs/r7_siting_probe/probe.log   # ends with 'probe done' (or the probe was stopped by hand)
LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod \
  bash deploy/aws/run_lanes.sh start ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt --max-threads 12 --dry-run
LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod \
  bash deploy/aws/run_lanes.sh start ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt --max-threads 12
# status / logs / stop: use the same LANES_DIR
LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod \
  bash deploy/aws/run_lanes.sh status ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt
```

* **Do not start batch 1 beside the probe.** The probe runs in tmux session `probe` with up to
  about 100 GB RSS and 12 threads; batch 1 (calibration about 65 GB, or four feasibility
  processes up to 96 GB) next to it would oversubscribe memory, and the 110 GB guard is per
  process, so nothing would stop it. The only step-2b input (`--root-import`) is read once, at
  the start of lane `b3_rootlp_s04`.
* `LANES_DIR` must be absolute or relative to the directory you run the command from;
  `run_lanes.sh` makes it absolute and passes it to the dispatcher. Use the same value for
  `status`, `stop` and `logs`. `sync_down.sh` fetches the folder (status files and lane logs).
* The first lane, `b0_gate`, runs `experiments/r7_gate.py`: it fails (exit 2) when a production
  marker is missing from the server tree, and every other lane waits behind it.

* One lanes file, six batches chained by `after` (batch n starts when batch n - 1 is done):
  1 calibration + one-site feasibility screen (4 processes) + held-out check, 2 m = 1
  (`r7_siting.py --stage m1`), 3 the 12 all-open root LPs (3 chains, at most 3 at once, the first
  imports the step-2b pool), 4 pair search, m = 3 additions, role table, 5 filtered comparison,
  DOT-only master, out of sample, 6 no-radius re-pricing. `--max-rss-gb 110` in every lane.
* Every command starts with `R7_BATCH=<n> R7_INSTANCE=r7i.4xlarge R7_USD_PER_H=1.0584`; each
  invocation appends a row to `outputs/r7_siting/cost.jsonl`. After `sync_down.sh`,
  `python3 experiments/r7_cost.py outputs/r7_siting` prints the cost per batch (plain sum and
  instance hours with overlapping lanes counted once); `RESULTS.md` and `SEARCH.md` include it.
* On an r7a.4xlarge, write the plan with `--instance r7a.4xlarge --usd-per-h 1.2172`.
* The analysis (`r7_siting.py --stage analyse`, `r7_search.py --stage report`, same flags) runs on
  the laptop after `sync_down.sh`. These two stages write no `cost.jsonl` row; rows without
  `R7_BATCH` are listed but left out of the total.
* A lane stopped with `run_lanes.sh stop` (SIGTERM) or `tmux kill-session` (SIGHUP) still writes
  its cost row (status `killed: ...`); a hard kill (OOM, instance stop) leaves a start row without
  an end row, counted as `unfinished` in the cost table.

## 10. Stop vs terminate, interruptions, resuming

* **Stop**: compute billing stops; the 200 GB volume (about 16 USD/month) and
  everything on it stay; the public IP changes on Start unless an Elastic IP is attached.
  Use Stop between work sessions.
* **Terminate**: the instance and (with "Delete on termination") its volume are deleted
  for good. Do it only after `sync_down.sh` has brought the results back. Terminate also releases
  the vCPU quota. **If the instance came from a persistent Spot request (Section 4.4), cancel the
  request first**: EC2 -> Spot Requests -> select it -> Actions -> Cancel request,
  and tick Terminate instances; otherwise AWS treats the terminated instance
  as an interruption and launches a **new** one, which keeps billing.
* **Spot interruption / reboot / crash**: every experiment is resumable by the keys of its
  `records.jsonl`; only the Gurobi solve that was in flight is repeated (at most one time limit per
  lane). After the instance is running again:
  ```bash
  . ~/battery_swap/env.sh
  bash ../deploy/aws/run_lanes.sh start outputs/cloud_lanes/lanes.txt
  ```
  Lanes that finished with exit code 0 are skipped, interrupted lanes get a `RESTART` line and run
  again, and lanes that had failed or were on hold are released and run again too (Section 9).
  Regenerate the lanes file first (`make_cloud_lanes.py`) if you want the retry lanes recomputed
  from the current records.
* **Optional auto-resume** after a Spot interruption or a reboot at night, so the instance does not
  sit idle (and billed) until you notice: on the server run `crontab -e` and add one line
  ```
  @reboot sleep 90 && bash /home/ubuntu/battery_swap/deploy/aws/run_lanes.sh start /home/ubuntu/battery_swap/ebike_swap_sim/outputs/cloud_lanes/lanes.txt >> /home/ubuntu/battery_swap/ebike_swap_sim/outputs/cloud_lanes/autoresume.log 2>&1
  ```
  (one line; the lane wrappers source `env.sh` themselves). Because this `start` also releases
  held and failed lanes, use `run_lanes.sh stop all` only when you intend to resume everything;
  remove the cron line (`crontab -r`) before a reboot you want to stay quiet.
* Growing or shrinking: Stop -> Change instance type -> Start -> `run_lanes.sh start`
  (the dispatcher reads the new `nproc`).

## 11. AWS Budgets: an alarm before the bill surprises you

1. Search "Billing and Cost Management" -> left menu Budgets -> Create
   budget.
2. Use a template: **Monthly cost budget**. Name `battery-swap-monthly`,
   amount e.g. **150 USD**, your e-mail. The template alerts at 85 % and 100 % of the actual spend
   and at 100 % forecast.
3. Optional second budget with the **Zero spend budget** template to catch anything
   left running by mistake once the project is over.
4. Also check Billing -> Bills weekly during the run; EC2 (compute + EBS) should be the only
   lines. Set the console to show cost in USD.

## 12. Getting the results back

```bash
deploy/aws/sync_down.sh --dry-run        # shows what would come back
deploy/aws/sync_down.sh                  # -> cloud_results/ebike_swap_sim/outputs/{r6_penalty,r6_fill,r6_o2,cloud_lanes}
```
By default the download lands in `cloud_results/` (git-ignored), a mirror of the server tree, so
that nothing the laptop is still writing is overwritten. Compare, then either copy the folders you
want into `ebike_swap_sim/outputs/` or, when no local experiment is running, run
`sync_down.sh --in-place` to write directly into `ebike_swap_sim/outputs/`. The server's
`records.jsonl` are append-only supersets of what was uploaded, so replacing a local file with the
server's copy is safe **unless the laptop appended to the same stage in the meantime** -- that is
the reason for the staging folder. The analysis tables (`RESULTS.md`, `*.csv`, `figs/`) are
regenerated locally at any time with the `--analyse` commands of the final lane. PDF figures
under `outputs/*/figs/` are the only PDFs `sync_down.sh` transfers (every other `*.pdf` is
excluded in both directions).

Instance dumps (`outputs/*/instances/`, large, regenerable) are not transferred unless
`--with-instances`.

## 13. Costs at a glance

| Item | Approximate cost |
|---|---|
| r7i.8xlarge on-demand, 24 h | 51 USD |
| r7i.8xlarge Spot, 24 h | 20-26 USD |
| r7i.2xlarge on-demand, 3 h setup | 1.6 USD |
| 200 GB gp3 volume | 16 USD per month while it exists (also when stopped) |
| Public IPv4 address (auto-assigned or Elastic IP) | 3.6 USD per month while the instance runs; an Elastic IP also bills while the instance is stopped or the address is unattached |
| Data transfer | first 100 GB out per month free; the results are well under 1 GB |

## 14. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `VcpuLimitExceeded` at launch | quota (Section 2); launch a smaller type meanwhile |
| `Permission denied (publickey)` | key path / `chmod 400` / user `ubuntu` / wrong key pair on the instance |
| ssh hangs | your public IP changed: edit the security group inbound rule (My IP) |
| `bootstrap.sh` licence FAIL | `~/gurobi/gurobi.lic` missing (run `upload_licence.sh`), or no outbound internet, or the WLS licence expired in the Gurobi portal |
| Gurobi error 10009 in a lane log | licence problem at run time: `. env.sh && bash ../deploy/aws/bootstrap.sh --checks-only` |
| `pip install` fails on torch | the instance must be x86_64 with internet; see the comment in `requirements.txt` |
| `rsync: ... failed` on the laptop | macOS ships openrsync; `brew install rsync` gives the full rsync (the scripts prefer it when present) |
| Lanes queue but never start | `run_lanes.sh status`: a lane's `after` dependency has not finished, or `--max-threads` is too small |
| Disk full | `df -h`; delete `outputs/*/instances/` and `scratch/`; 200 GB is ample for round 6 |
| Instance stopped by itself | Spot interruption: Instance state -> Start, then `run_lanes.sh start` (or the cron line of Section 10) |
| A new instance appeared after Terminate | the persistent Spot request is still open: Spot Requests -> Cancel request with Terminate instances |
| `Could not get lock /var/lib/dpkg/lock-frontend` | Ubuntu's automatic updater on a fresh boot; `bootstrap.sh` waits up to 10 min, otherwise re-run it two minutes later |
| `bootstrap.sh` dies when the laptop sleeps | run it inside tmux as in Section 8; `tmux attach -t boot`, `~/bootstrap.log` |
| A lane shows `failed (rc=N)` | `run_lanes.sh logs <name>`; fix (licence, memory, flag), then `run_lanes.sh start` releases it; dependents wait meanwhile |
| Lanes are slower than on the laptop | expected: vCPUs are hyperthreads (Section 4.2); lower `--max-threads` (16 = one thread per core) rather than raising it |

## 15. Security checklist

* SSH only from My IP; no other inbound rule; no password login (the Ubuntu AMI has none).
* Key in `~/.ssh` with mode 400; licence on the Desktop and on the server with mode 600; `*.pem`
  and `*.lic` are in `.gitignore` and excluded by the sync scripts in both directions.
* `aws_env.sh` holds only host names and paths, is git-ignored (also `aws_env.*.sh` copies) and
  should have mode 600 (the scripts warn otherwise). Run `git status` before every push: nothing
  under `deploy/aws/` except the scripts, this README, `aws_env.example.sh` and `requirements.txt`
  should appear.
* When the project is over: cancel any persistent Spot request, terminate the instance, release
  the Elastic IP, delete leftover volumes and snapshots; keep the budget alarm.
