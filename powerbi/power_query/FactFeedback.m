let
    Source = StagingDatabase{[Schema = "support_analytics", Item = "customer_feedback"]}[Data],
    Selected = Table.SelectColumns(Source, {
        "feedback_id", "ticket_id", "customer_id", "submitted_at", "csat_score"
    }),
    Typed = Table.TransformColumnTypes(Selected, {
        {"feedback_id", type text}, {"ticket_id", type text}, {"customer_id", type text},
        {"csat_score", Int64.Type}
    }),
    UtcTimestamps = Table.TransformColumns(Typed, {
        {"submitted_at", each fnUtcDateTime(_), type nullable datetime}
    }),
    AddedSubmittedDate = Table.AddColumn(UtcTimestamps, "submitted_date", each Date.From([submitted_at]), type date),
    AddedPositive = Table.AddColumn(AddedSubmittedDate, "is_positive_csat", each [csat_score] >= 4, type logical)
in
    AddedPositive
