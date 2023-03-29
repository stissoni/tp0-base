# TP0: Docker + Comunicaciones + Concurrencia

En el presente repositorio se provee un ejemplo de cliente-servidor el cual corre en containers con la ayuda de [docker-compose](https://docs.docker.com/compose/). El mismo es un ejemplo práctico brindado por la cátedra para que los alumnos tengan un esqueleto básico de cómo armar un proyecto de cero en donde todas las dependencias del mismo se encuentren encapsuladas en containers. El cliente (Golang) y el servidor (Python) fueron desarrollados en diferentes lenguajes simplemente para mostrar cómo dos lenguajes de programación pueden convivir en el mismo proyecto con la ayuda de containers.

Por otro lado, se presenta una guía de ejercicios que los alumnos deberán resolver teniendo en cuenta las consideraciones generales descriptas al pie de este archivo.

## Instrucciones de uso

Buildear las imagenes del cliente y del servidor

```
docker build -f ./server/Dockerfile -t "server:latest" .
```

```
docker build -f ./client/Dockerfile -t "client:latest" .
```

Ejecutar docker compose para levantar el servidor junto a los clientes utilizando el profile prod

```
docker compose -f docker-compose-dev.yaml --profile prod up -d --build
```
