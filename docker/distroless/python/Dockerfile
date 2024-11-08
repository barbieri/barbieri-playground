FROM gcr.io/distroless/python3

WORKDIR /app
ENV TEST_ENVVAR_FILE=/app/dockerfile-example-app.py
ENV TEST_HOST=google.com
ENV TEST_PORT=80
ENV DEBUG=0

COPY ./docker_entrypoint.py /
COPY ./dockerfile-example-app.py ./

# alternatively: ENTRYPOINT ["/usr/bin/python3", ...
CMD [ \
    "/docker_entrypoint.py", \
    "--file-env=TEST_ENVVAR", \
    "--wait-server=${TEST_HOST}:${TEST_PORT}", \
    "./dockerfile-example-app.py", \
    "example-argment", \
    "--test=$TEST_HOST:$TEST_PORT" \
]
