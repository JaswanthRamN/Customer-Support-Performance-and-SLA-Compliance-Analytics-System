#!/bin/sh
set -eu

psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
  --dbname customer_support_analytics --file /opt/customer-support/schema.sql
psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" \
  --dbname customer_support_analytics --file /opt/customer-support/reporting_views.sql
