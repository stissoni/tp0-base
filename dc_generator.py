import yaml

N_CLIENTS = 3

my_dict = {
    "networks": {
        "testing_net": {
            "ipam": {"driver": "default", "config": [{"subnet": "172.25.125.0/24"}]}
        }
    },
    "services": {
        "server": {
            "container_name": "server",
            "image": "server:latest",
            "entrypoint": "python3 /main.py",
            "environment": ["PYTHONUNBUFFERED=1", "LOGGING_LEVEL=DEBUG"],
            "networks": ["testing_net"],
        }
    },
    "version": "3.9",
}

for i in range(N_CLIENTS):
    client = f"client{i+1}"

    my_dict["services"][client] = {
        "container_name": f"{client}",
        "image": "client:latest",
        "entrypoint": "/client",
        "environment": [f"CLI_ID={i+1}", "LOGGING_LEVEL=DEBUG"],
        "networks": ["testing_net"],
        "depends_on": ["server"],
    }


with open("docker-compose-dev.yaml", "w") as f:
    yaml.dump(my_dict, f)
