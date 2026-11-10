FROM postgres:17-alpine

COPY docker/postgres/init/00-create-databases.sql /docker-entrypoint-initdb.d/00-create-databases.sql
COPY docker/postgres/init/10-initialize-analytics.sh /docker-entrypoint-initdb.d/10-initialize-analytics.sh
COPY sql/schema.sql /opt/customer-support/schema.sql
COPY sql/reporting_views.sql /opt/customer-support/reporting_views.sql
RUN chmod 0755 /docker-entrypoint-initdb.d/10-initialize-analytics.sh
