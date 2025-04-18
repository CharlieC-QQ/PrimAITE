# PrimAITE

![image](./PrimAITE_logo_transparent.png)

The ARCD Primary-level AI Training Environment (**PrimAITE**) provides an effective simulation capability for the purposes of training and evaluating AI in a cyber-defensive role. It incorporates the functionality required of a primary-level ARCD environment, which includes:

- The ability to model a relevant platform / system context;

- The ability to model key characteristics of a platform / system by representing connections, IP addresses, ports, traffic loading, operating systems and services;

- Operates at machine-speed to enable fast training cycles.

PrimAITE presents the following features:

- Highly configurable (via YAML files) to provide the means to model a variety of platform / system laydowns and adversarial attack scenarios;

- A Reinforcement Learning (RL) reward function based on (a) the ability to counter the specific modelled adversarial cyber-attack, and (b) the ability to ensure success;

- Provision of logging to support AI evaluation and metrics gathering;

- Realistic network traffic simulation, including address and sending packets via internet protocols like TCP, UDP, ICMP, and others

- Routers with traffic routing and firewall capabilities

- Support for multiple agents, each having their own customisable observation space, action space, and reward function definition, and either deterministic or RL-directed behaviour

Whilst PrimAITE ships with a number of example modelled scenarios (a.k.a. Use Cases), it has not been developed to mandate the solving of a single cyber challenge, and instead provides a highly flexible environment application that can be extended and reconfigured by the user to suit their specific cyber defence training and evaluation needs. PrimAITE provides default networks, red agent and green agent behaviour, reward functions, and action / observation space configuration, all of which can be utilised out of the box, but which ultimately can (and in some instances should) be built upon and / or reconfigured to meet the needs of different defensive agent developers. The PrimAITE user guide provides comprehensive instruction on all PrimAITE features, functionality and components, and can be consulted in order to help guide users in any reconfiguration or enhancements they wish to undertake; a library of example Jupyter notebooks are also provided to support such work.

## Getting Started with PrimAITE

### 💫 Installation
**PrimAITE** is designed to be OS-agnostic, and thus should work on most variations/distros of Linux, Windows, and MacOS.
Currently, the PrimAITE wheel can only be installed from GitHub. This may change in the future with release to PyPi.

#### Windows (PowerShell)

**Prerequisites:**
* Manual install of Python >= 3.9 < 3.12

**Install:**

``` powershell
mkdir ~\primaite
cd ~\primaite
python3 -m venv .venv
attrib +h .venv /s /d # Hides the .venv directory
.\.venv\Scripts\activate
pip install primaite-{VERSION}-py3-none-any.whl[rl]
primaite setup
```


#### Unix

**Prerequisites:**
* Manual install of Python >= 3.8 < 3.12

``` bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.10
sudo apt-get install python3-pip
sudo apt-get install python3-venv
```
**Install:**

``` bash
mkdir ~/primaite
cd ~/primaite
python3 -m venv .venv
source .venv/bin/activate
pip install primaite-{VERSION}-py3-none-any.whl[rl]
primaite setup
```



### Developer Install from Source
To make your own changes to PrimAITE, perform the install from source (developer install)

#### 1. Clone the PrimAITE repository
``` unix
git clone git@github.com:Autonomous-Resilient-Cyber-Defence/PrimAITE.git
```

#### 2. CD into the repo directory
``` unix
cd PrimAITE
```
#### 3. Create a new python virtual environment (venv)

```unix
python3 -m venv venv
```

#### 4. Activate the venv

##### Unix
```bash
source venv/bin/activate
```

##### Windows (Powershell)
```powershell
.\venv\Scripts\activate
```

#### 5. Install `primaite` with the dev extra into the venv along with all of it's dependencies

```bash
python3 -m pip install -e .[dev,rl]
```

#### 6. Perform the PrimAITE setup:

```bash
primaite setup
```

#### Note
*It is possible to install PrimAITE without Ray RLLib, StableBaselines3, or any deep learning libraries by omitting the `rl` flag in the pip install command.*

### Running PrimAITE

Use the provided jupyter notebooks as a starting point to try running PrimAITE. They are automatically copied to your PrimAITE notebook folder when you run `primaite setup`.

#### 1. Activate the virtual environment

##### Windows (Powershell)
```powershell
.\venv\Scripts\activate
```

##### Unix
```bash
source venv/bin/activate
```

#### 2. Open jupyter notebook

```bash
python -m jupyter notebook
```
Then, click the URL provided by the jupyter command to open the jupyter application in your browser. You can also open notebooks in your IDE if supported.

## 📚 Documentation

### Pre requisites

Building the documentation requires the installation of Pandoc

##### Unix
```bash
sudo apt-get install pandoc
```

##### Other operating systems
Follow the steps in https://pandoc.org/installing.html

### Building the documentation

The PrimAITE documentation can be built with the following commands:

##### Unix
```bash
cd docs
make html
```

##### Windows (Powershell)
```powershell
cd docs
.\make.bat html
```


## Example notebooks
Check out the example notebooks to learn more about how PrimAITE works and how you can use it to train agents. They are automatically copied to your primaite installation directory when you run `primaite setup`.
