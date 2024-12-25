# MicroOVN Rebuilder

This simple script aims to leverage [MicroOVN](https://github.com/canonical/microovn) for
development of [OVN](https://github.com/ovn-org/ovn). MicroOVN can be used to simplify
OVN cluster deployment and this tool will manage building OVN locally from source and
replacing relevant binaries in the cluster when they get changed by the build.

> **Important**
> 
> MicroOVN is a snap package, to be able to modify its files at runtime, it has to be
> installed in with `snap try` as opposed to `snap install`. More info about `snap try`
> is in the [Snap documentation](https://snapcraft.io/docs/snap-try).

## Installation

This is a python script, so you are welcome to install it in any way that works for you.
However, the easiest way would be to use [poetry](https://python-poetry.org).

```bash
git clone https://github.com/mkalcok/microovn-rebuilder.git
cd microovn-rebuilder
poetry install --only main
```

## Usage

When `microovn-rebuilder` is executed, it runs continually in the foreground, waiting
for input from user when `OVN` sources should be rebuilt and synced to the remote
deployment. See `--help` for available flags and options.

> **Note:**
> 
> `microovn-rebuilder` is currently not packaged for global installation. All examples
> of usage below expect you to execute them within the project's root directory

**Example:**
```
$ poetry run microovn-rebuilder -c ./default_config.yaml -o ~/code/ovn/ -H lxd:movn1,lxd:movn2,lxd:movn3
Press 'Enter' to rebuild and deploy OVN. (Ctrl-C for exit)
```

The above example does following:
  * reads configuration file `./default_config.yaml`
  * starts watching for changes of files defined in the config within the `~/code/ovn/`
  * waits for user to press `Enter`

When user presses `Enter`:
  * runs `make` in the `~/code/ovn` directory
  * syncs any watched files that have been changed by the build to the LXD containers/VMs
    `movn1`, `movn2` and `movn3`
  * runs actions defined in the config file on the remote hosts
  * loops back to user prompt

## Configuration

This tool is primarily driven by `yaml` config file that defines which files should be
watched in the local build directory, where they should be synced on change and which
services should be restarted after the sync. This repository contains example confing
file `default_config.yaml`.

**Config file format:**
```yaml
# List of targets that should be watched. Each target is a dictionary
targets:
    # relative path to file that should be watched for changes (within the local OVN directory)
  - local_path: northd/ovn-northd
    # relative path to which the watched file will be synced on change (within the remote MicroOVN installation)
    remote_path: bin/ovn-northd
    # Snap service that should be restarted if this file is synced
    service: microovn.ovn-northd
```

## Example of simple deployment from scratch

Let's assume that:
  * You have OVN source code in `~/code/ovn`
  * You have `microovn-rebuilder` downloaded and installed in `~/code/microovn-rebuilder`
  * You have initialized LXD (for creating containers that will run our OVN cluster)

### Prepare OVN/OVS source code
Install OVN/OVS build dependencies listed in 
[their documentation](https://docs.ovn.org/en/latest/intro/install/general.html#build-requirements).

Now we can bootstrap and configure both projects.
```bash
cd ~/code/ovn
./boot.sh

# bootstrap and configure OVS
cd ovs/
./boot.sh
./configure --enable-ssl
make

# back to the OVN
cd ../
./configure --with-ovs-source=../ovs --enable-ssl
```

(If the build instructions get out of date, please refer to the
[official OVN documentation](https://docs.ovn.org/en/latest/intro/install/general.html))

### Create OVN cluster on LXD containers

To develop clustered software like `OVN`, its good to test changes in a clustered
environment. For that we'll create three LXD containers, `movn1`, `movn2` and `movn3`.

```bash
lxc launch ubuntu:lts movn1
lxc launch ubuntu:lts movn2
lxc launch ubuntu:lts movn3
```

Now we can install `microovn` in each container using
[snap try](https://snapcraft.io/docs/snap-try).

```bash
# shell into the first container
lxc exec movn1 bash

# install microovn with "snap try"
snap download --basename=microovn microovn
unsquashfs microovn.snap
snap try ./squashfs-root/
# For locally installed snaps, we need to manually connect its plugs
for plug in firewall-control \
             hardware-observe \
             hugepages-control \
             network-control \
             openvswitch-support \
             process-control \
             system-trace; do \
    sudo snap connect microovn:$plug;done
## run above commands on each container
```

(If the installation instruction get out of date, please refer to the
[official MicroOVN documentation](https://canonical-microovn.readthedocs-hosted.com/en/latest/developers/building/#install-microovn))

Now we can initialize OVN cluster, start with the first container
```bash
# shell into the first container
lxc exec movn1 bash

# bootstrap the cluster
microovn cluster bootstrap
# create access tokens for the other members
microovn cluster add movn2
microovn cluster add movn3
```

Join the cluster with second container
```bash
# shell into the second container
lxc exec movn2 bash

# join the cluster with the token generated for this container
microovn cluster join <token_for_movn2>
```

And finally repeat the "join process" on the third container.

### Start using `microovn-rebuilder`

With the OVN source code prepared and the cluster ready, we can get to work. Start
`microovn-rebuilder` in the separate console.

```bash
cd ~/code/microovn-rebuilder
poetry run microovn-rebuilder -c ./default_config.yaml -o ~/code/ovn -H lxd:movn1,lxd:movn2,lxd:movn3
```

Now you can start editing your `OVN` source files and when you are ready to deploy your
changes, you can hit `Enter` in the console running the `microovn-rebuilder`. You'll see
output like this:

```
Press 'Enter' to rebuild and deploy OVN. (Ctrl-C for exit)
[local] Rebuilding OVN at ~/code/ovn

[movn1] Removing remote file /root/squashfs-root/bin/ovn-northd
[movn1] Uploading file ~/code/ovn/northd/ovn-northd to /root/squashfs-root/bin/ovn-northd
[movn1] Restarting microovn.ovn-northd

[movn2] Removing remote file /root/squashfs-root/bin/ovn-northd
[movn2] Uploading file ~/code/ovn/northd/ovn-northd to /root/squashfs-root/bin/ovn-northd
[movn2] Restarting microovn.ovn-northd

[movn3] Removing remote file /root/squashfs-root/bin/ovn-northd
[movn3] Uploading file ~/code/ovn/northd/ovn-northd to /root/squashfs-root/bin/ovn-northd
[movn3] Restarting microovn.ovn-northd
Press 'Enter' to rebuild and deploy OVN. (Ctrl-C for exit)
```

## Supported remote connectors

This tool is primarily meant to sync OVN binaries to the remote hosts running the
cluster. Following connectors are currently supported:
  * LXD

## Caveats

  * To be able to edit/replace files on the cluster, MicroOVN has to be installed via
    ["snap try"](https://snapcraft.io/docs/snap-try)
  * Version of OVN installed on the cluster, by the MicroOVN, must roughly match the
    version of the source file you are editing.

## Contributing

While this is admittedly very small and niche project, any contributions are welcome. Be
it in a form of Github issues or Pull Requests. For pul requests to be merged, they need
to pass CI pipeline (tests/linters). You can get ahead of the game by running them
locally before pushing.

## Running tests locally

All tests related to the python code are defined as "tox environments" and can be
executed using `poetry`, provided that dependencies from `dev` group are installed (
it should be taken care of by simply running `poetry install`.

### Formatting code

This project uses set of opinionated code formatters to keep the code style consistent,
you can run them with:

```bash
poetry run tox -e format
```

### Linting code

To see if any of the linters have objections to the code, run:

```bash
poetry run tox -e lint
```

### Unit tests

This project aims to keep 100% code coverage (with few explicit exemptions). To execute
all unit tests, along with the coverage report, run:

```bash
poetry run tox -e unit
```

Note that this command may "fail" if the coverage is not sufficient.

## Todo
* Support execution of arbitrary scripts aside from just restarting services on file
  updates. This will enable syncing things like OVSDB schemas as they require migration
  execution of a migration script instead of just a service restart.
* Add SSH connector
* Add automation for bootstrapping local OVN source repository
* Add automation for bootstrap remote cluster
* Add command that lists supported remote connectors
* Allow mixing connectors of different types