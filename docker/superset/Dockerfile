FROM apache/superset:4.1.1

USER root

RUN python -m pip install --no-cache-dir psycopg2-binary

COPY docker/superset/superset-init.sh /app/superset-init.sh
RUN chmod +x /app/superset-init.sh

USER superset

CMD ["/app/superset-init.sh"]
