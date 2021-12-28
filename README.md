# KLab Server Side Camp (vol.1)

## Requirements

```sh
sudo apt-get install -y mysql-server libmysqlclient-dev
```

```sh
poetry install
```

## format

```sh
poetry run nox --session format
poetry run nox --session lint
```
