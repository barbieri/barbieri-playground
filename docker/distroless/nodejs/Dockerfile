FROM gcr.io/distroless/nodejs

WORKDIR /app
ENV TEST_ENVVAR_FILE=/app/dockerfile-example-app.js
ENV TEST_HOST=google.com
ENV TEST_PORT=80
ENV DEBUG=0

COPY ./docker-entrypoint.min.js /
COPY ./dockerfile-example-app.js ./

# alternatively: ENTRYPOINT ["/nodejs/bin/node", ...
CMD [ \
    "/docker-entrypoint.min.js", \
    "--file-env=TEST_ENVVAR", \
    "--wait-server=${TEST_HOST}:${TEST_PORT}", \
    "./dockerfile-example-app.js", \
    "example-argment", \
    "--test=$TEST_HOST:$TEST_PORT" \
]
