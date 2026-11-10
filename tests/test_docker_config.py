"""Static container configuration contracts; Docker is optional in local tests."""

from pathlib import Path
import unittest

import yaml

from scripts.generate_synthetic_data import ROOT


class DockerConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose_path = ROOT / "compose.yaml"
        cls.compose_text = cls.compose_path.read_text(encoding="utf-8")
        cls.compose = yaml.safe_load(cls.compose_text)

    def test_required_services_and_named_volumes_exist(self):
        self.assertEqual(
            {"postgres", "fastapi", "django", "airflow-init", "airflow-webserver", "airflow-scheduler"},
            set(self.compose["services"]),
        )
        self.assertIn("postgres_data", self.compose["volumes"])
        self.assertIn("airflow_logs", self.compose["volumes"])
        self.assertIn("pipeline_processed", self.compose["volumes"])
        self.assertIn("pipeline_reports", self.compose["volumes"])

    def test_service_name_networking_and_database_persistence(self):
        for service in ("fastapi", "django"):
            self.assertEqual(self.compose["services"][service]["environment"]["PGHOST"], "postgres")
            self.assertEqual(self.compose["services"][service]["environment"]["PGDATABASE"],
                             "customer_support_analytics")
        postgres_mounts = self.compose["services"]["postgres"]["volumes"]
        self.assertIn("postgres_data:/var/lib/postgresql/data", postgres_mounts)
        self.assertIn("pipeline_processed:/app/data/processed",
                      self.compose["services"]["fastapi"]["volumes"])
        self.assertIn("pipeline_reports:/opt/airflow/project/reports",
                      self.compose["services"]["airflow-scheduler"]["volumes"])

    def test_health_checks_and_dependency_conditions(self):
        for service in ("postgres", "fastapi", "django", "airflow-webserver", "airflow-scheduler"):
            self.assertIn("healthcheck", self.compose["services"][service])
        self.assertEqual(self.compose["services"]["fastapi"]["depends_on"]["postgres"]["condition"],
                         "service_healthy")
        self.assertEqual(
            self.compose["services"]["airflow-webserver"]["depends_on"]["airflow-init"]["condition"],
            "service_completed_successfully",
        )

    def test_secrets_are_variable_substitutions_not_committed_values(self):
        self.assertIn("${POSTGRES_PASSWORD", self.compose_text)
        self.assertIn("${DJANGO_SECRET_KEY", self.compose_text)
        self.assertIn("${AIRFLOW_ADMIN_PASSWORD", self.compose_text)
        self.assertNotIn("change-me-postgres-password", self.compose_text)

    def test_dockerfiles_use_expected_entrypoints(self):
        fastapi = (ROOT / "docker" / "fastapi" / "Dockerfile").read_text(encoding="utf-8")
        django = (ROOT / "docker" / "django" / "Dockerfile").read_text(encoding="utf-8")
        postgres = (ROOT / "docker" / "postgres" / "Dockerfile").read_text(encoding="utf-8")
        airflow = (ROOT / "docker" / "airflow" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("api.main:create_app", fastapi)
        self.assertIn("USER app", fastapi)
        self.assertIn("ticket_service.config.wsgi:application", django)
        self.assertIn("USER app", django)
        self.assertIn("schema.sql", postgres)
        self.assertIn("reporting_views.sql", postgres)
        self.assertIn("apache/airflow", airflow)

    def test_postgres_initialization_order_creates_both_databases(self):
        sql = (ROOT / "docker" / "postgres" / "init" / "00-create-databases.sql").read_text(
            encoding="utf-8")
        script = (ROOT / "docker" / "postgres" / "init" /
                  "10-initialize-analytics.sh").read_text(encoding="utf-8")
        self.assertIn("CREATE DATABASE customer_support_analytics", sql)
        self.assertIn("CREATE DATABASE airflow", sql)
        self.assertIn("--dbname customer_support_analytics", script)
        self.assertIn("--set ON_ERROR_STOP=1", script)


if __name__ == "__main__":
    unittest.main()
