## Betarigs Manager CLI

Python 2.x script for automating [Betarigs](https://betarigs.com) rentals and pool updates. If a web-based PHP control panel sounds preferable check out my [other repository](https://github.com/sathoro/betarigs-manager) that serves the same purpose.


### Installation

    pip install requests cement
    git clone https://github.com/sathoro/betarigs-manager-cli.git
    cd betarigs-manager-cli
    python main.py setup
    
### Setup

Run `python main.py setup` or simply edit `manager.conf`.

### Usage

    python main.py rent
    or
    python main.py update-pool
