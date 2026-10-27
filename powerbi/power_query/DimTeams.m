let
    Source = StagingDatabase{[Schema = "support_analytics", Item = "teams"]}[Data],
    Selected = Table.SelectColumns(Source, {"team_id", "team_name", "specialization"}),
    Typed = Table.TransformColumnTypes(Selected, {
        {"team_id", type text}, {"team_name", type text}, {"specialization", type text}
    })
in
    Typed
