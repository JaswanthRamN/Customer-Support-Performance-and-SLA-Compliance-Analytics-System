let
    Source = StagingDatabase{[Schema = "support_analytics", Item = "agents"]}[Data],
    Selected = Table.SelectColumns(Source, {
        "agent_id", "agent_label", "team_id", "hired_at", "experience_level"
    }),
    Typed = Table.TransformColumnTypes(Selected, {
        {"agent_id", type text}, {"agent_label", type text}, {"team_id", type text},
        {"experience_level", type text}
    }),
    UtcTimestamps = Table.TransformColumns(Typed, {
        {"hired_at", each fnUtcDateTime(_), type nullable datetime}
    })
in
    UtcTimestamps
