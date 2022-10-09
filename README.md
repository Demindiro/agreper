# Agreper - minimal, no-JS forum software

Agreper is a forum board with a focus on being easy to set up and manage.

## Features

## Install & running

### Linux

First clone or [download the latest release](todo).

Then setup with:

```
make
./init_sqlite.sh forum.db
```

Lastly, run with:

```
./run_sqlite.sh forum.db forum.pid
```

You will need a proxy such as nginx to access the forum on the public internet.
