let
    Source = PostgreSQL.Database(
        pServer,
        pDatabase,
        [CreateNavigationProperties = false, CommandTimeout = #duration(0, 0, 10, 0)]
    )
in
    Source
